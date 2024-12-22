from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta


class ShipmentOut(metaclass=PoolMeta):
    """
    ShipmentOut class extends the stock.shipment.out model to include
    scrap lines.
    """
    __name__ = 'stock.shipment.out'

    scrap_lines = fields.One2Many('scrap.line', 'shipment', 'Scrap Lines')
    related_scrap_lines = fields.One2Many('scrap.shipment',
           'shipment', 'Related Scrap Lines')

    @classmethod
    @ModelView.button
    def pack(cls, shipments):
        """
        Overrides the pack method to handle scrap lines associated with
        the shipment. Deletes existing scrap lines and creates new ones
        based on the outgoing moves.
        """
        pool = Pool()
        ScrapLine = pool.get('scrap.line')
        scrap_lines = []
        super().pack(shipments)
        to_delete = []
        for shipment in cls.browse([x.id for x in shipments]):
            for move in shipment.outgoing_moves:
                to_delete += move.scrap_lines
                scrap_lines += move.get_scrap_lines()

        ScrapLine.delete(to_delete)
        ScrapLine.save(scrap_lines)


class StockMove(metaclass=PoolMeta):
    """
    StockMove class extends the stock.move model to include scrap lines.
    """
    __name__ = 'stock.move'

    scrap_lines = fields.One2Many('scrap.line', 'move', 'Scrap Lines')

    def get_scrap_lines(self):
        """
        Generates scrap lines based on the product's scrap template lines
        and the move's quantity.
        """

        pool = Pool()
        ScrapLine = pool.get('scrap.line')

        scrap_lines = []
        for sline in self.product.template.scrap_template_lines:
            template = sline.product.template
            scrap_line = ScrapLine()
            scrap_line.category = template.scrap_category
            scrap_line.product = sline.product
            scrap_line.quantity = round(sline.get_quantity() * self.quantity, 4)
            scrap_line.weight = round(sline.get_weight() * self.quantity, 4)
            scrap_line.move = self
            scrap_line.shipment = self.shipment
            scrap_line.party = template.scrap_category.party
            scrap_line.cost_price = template.scrap_category.cost_price
            scrap_lines.append(scrap_line)
        return scrap_lines

