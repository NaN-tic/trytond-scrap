from decimal import Decimal

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
    scrap_amount = fields.Function(fields.Numeric('Scrap Amount'),
        'get_scrap_amount')

    def get_scrap_amount(self, name):
        amount = 0
        for scrap in self.related_scrap_lines:
            amount += scrap.weight * float(scrap.cost_price)
        return Decimal(amount).quantize(Decimal('0.0001'))

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
        for l in scrap_lines:
            l.save()

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
        scrap_lines = []
        for sline in self.product.template.scrap_template_lines:
            lines = sline._get_scrap_line(self.quantity)
            for line in lines:
                line.shipment = self.shipment
                line.move = self
            scrap_lines += lines
        return scrap_lines
