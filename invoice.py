from decimal import Decimal

from sql.aggregate import Literal, Max, Sum
from sql.operators import Concat
from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

from .product import ScrapMixin


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    related_scrap_lines = fields.One2Many('scrap.invoice', 'invoice',
        'Related Scrap Lines')
    scrap_amount = fields.Function(fields.Numeric('Scrap Amount'),
        'get_scrap_amount')

    def get_scrap_amount(self, name):
        amount = 0
        for scrap in self.related_scrap_lines:
            amount += scrap.weight * float(scrap.cost_price)
        return Decimal(amount).quantize(Decimal('0.0001'))


class ScrapInvoice(ModelSQL, ModelView, ScrapMixin):
    'Scrap Invoice'
    __name__ = 'scrap.invoice'


    @classmethod
    def table_query(cls):
        pool = Pool()
        Shipment = pool.get('stock.shipment.out')
        Scrap = pool.get('scrap.line')
        StockMove = pool.get('stock.move')
        Invoice = pool.get('account.invoice')
        MoveRel = pool.get('account.invoice.line-stock.move')
        InvoiceLine = pool.get('account.invoice.line')

        shipment = Shipment.__table__()
        scrap = Scrap.__table__()
        stock_move = StockMove.__table__()
        invoice = Invoice.__table__()
        stock_move_rel = MoveRel.__table__()
        line = InvoiceLine.__table__()

        cursor = Transaction().connection.cursor()
        cursor.execute(*invoice.select(Max(invoice.id)))
        max_id, = cursor.fetchone()
        id_padding = 10 ** len(str(max_id))

        query = invoice.join(
            line, condition=line.invoice == invoice.id
            ).join(
            stock_move_rel, condition=line.id == stock_move_rel.invoice_line
            ).join(
            stock_move, condition=stock_move.id == stock_move_rel.stock_move
            ).join(
            shipment, condition= (stock_move.shipment ==
                    Concat('stock.shipment.out,', shipment.id))
            ).join(
                scrap, condition=shipment.id == scrap.shipment
            )

        query = query.select(
                scrap.product,
                scrap.category,
                Sum(scrap.quantity).as_('quantity'),
                Sum(scrap.weight).as_('weight'),
                (invoice.id + Literal(id_padding)
                    + scrap.product).as_('id'),
                invoice.id.as_('invoice'),
                Max(scrap.write_uid).as_('write_uid'),
                Max(scrap.create_uid).as_('create_uid'),
                Max(scrap.write_date).as_('write_date'),
                Max(scrap.create_date).as_('create_date'),
                Max(scrap.cost_price).as_('cost_price'),
                Literal(None).as_('move'),
                Literal(None).as_('shipment'),
                Literal(None).as_('invoice_line'),
                scrap.party,
                group_by=(scrap.product, scrap.category, scrap.shipment,
                    scrap.party, invoice.id)
        )

        return query
