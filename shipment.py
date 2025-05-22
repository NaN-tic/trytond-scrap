from decimal import Decimal
from trytond.pyson import Eval
from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class ShipmentOut(metaclass=PoolMeta):
    """
    ShipmentOut class extends the stock.shipment.out model to include
    scrap lines.
    """
    __name__ = 'stock.shipment.out'

    scrap_lines = fields.One2Many('scrap.line', 'shipment', 'Scrap Lines',
        states={
            'readonly': Eval('state').in_(['done', 'cancelled']),
        })
    # TODO: make table_query work for performance improvement
    # related_scrap_lines = fields.One2Many('scrap.shipment',
    #        'shipment', 'Related Scrap Lines')

    related_scrap_lines = fields.Function(fields.One2Many('scrap.line',
        'shipment', 'Related Scrap Lines'), 'on_change_with_related_scrap_lines')
    scrap_amount = fields.Function(fields.Numeric('Scrap Amount',
        digits=(16, 4)), 'get_scrap_amount')

    def get_scrap_amount(self, name):
        amount = 0
        for scrap in self.related_scrap_lines:
            amount += scrap.weight * float(scrap.cost_price)
        return Decimal(amount).quantize(Decimal('0.0001'))

    @fields.depends('moves')
    def on_change_with_related_scrap_lines(self, name=None):
        pool = Pool()
        Scrap = pool.get('scrap.line')

        scrap_lines = Scrap.search([
            ('shipment', '=', self.id),
            ])
        return scrap_lines

    @classmethod
    def copy(cls, shipments, default=None):
        default = default.copy() if default is not None else {}
        default.setdefault('scrap_lines')
        return super().copy(shipments, default=default)

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
            to_delete += shipment.scrap_lines
            for move in shipment.outgoing_moves:
                to_delete += move.scrap_lines
                scrap_lines += move.get_scrap_lines()

        to_delete = list(set(to_delete))
        ScrapLine.delete(to_delete)
        context = Transaction().context.copy()

        context['explode_scrap'] = False
        with Transaction().set_context(context):
            ScrapLine.create([x._save_values for x in scrap_lines])

    @classmethod
    @ModelView.button
    def pick(cls, shipments):
        pool = Pool()
        ScrapLine = pool.get('scrap.line')
        super().pick(shipments)
        to_delete = []
        for shipment in cls.browse([x.id for x in shipments]):
            to_delete += shipment.scrap_lines
            for move in shipment.outgoing_moves:
                to_delete += move.scrap_lines
        to_delete = list(set(to_delete))
        ScrapLine.delete(to_delete)


class StockMove(metaclass=PoolMeta):
    """
    StockMove class extends the stock.move model to include scrap lines.
    """
    __name__ = 'stock.move'

    scrap_lines = fields.One2Many('scrap.line', 'move', 'Scrap Lines',
        states={
            'readonly': Eval('state').in_(['done', 'cancelled']),
        })

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

    @classmethod
    def copy(cls, moves, default=None):
        default = default.copy() if default is not None else {}
        default.setdefault('scrap_lines')
        return super().copy(moves, default=default)
