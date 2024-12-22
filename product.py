from sql.aggregate import Literal, Max, Sum
from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class ScrapCategory(ModelSQL, ModelView):
    'Scrap Category'
    __name__ = 'scrap.category'

    name = fields.Char('Name', required=True)
    category = fields.Selection(
        [('domestic', 'Domestic'),
         ('industrial', 'Industrial'),
         ('commercial', 'Commercial')],
        'Scrap Category', required=True)
    party = fields.Many2One('party.party', 'Party', required=True,
        help='''Responsible Third Party :Declaration of the producer
        extended responsibility system or systems with which they meet
        their obligations for each category of packaging, attaching a
        certificate of participation in collective systems or the environmental
        identification number in the case of individual systems.''')
    type_ = fields.Selection(
        [('single_use', 'Single Use'),
         ('reusable', 'Reusable'),
         ('both', 'Both')],
        'Scrap Type', required=True)
    cost_price = fields.Numeric('Cost', digits=(16, 6), required=True)


class ScraplineTemplate(ModelSQL, ModelView):
    'Scrap Template Line'
    __name__ = 'scrap.template.line'

    template = fields.Many2One('product.template', 'Template', required=True)
    product = fields.Many2One('product.product', 'Scrap   Product',
        required=True)
    quantity_formula = fields.Char('Quantity Formula', required=True)
    weight_formula = fields.Char('Weight Formula', required=True)

    def get_quantity(self):
        return eval(self.quantity_formula)

    def get_weight(self):
        return eval(self.weight_formula)


class ScrapProductMixin():
    __slots__ = ()

    scrap_category = fields.Many2One('scrap.category', 'Scrap Category')
    scrap_package = fields.Boolean('Scrap Package')
    scrap_template_lines = fields.One2Many('scrap.template.line', 'template',
        'Scrap Lines')


class ProductTemplate(ScrapProductMixin, metaclass=PoolMeta):
    __name__ = 'product.template'


class ScrapMixin():
    __slots__ = ()

    category = fields.Many2One('scrap.category', 'Category', required=True)
    product = fields.Many2One('product.product', 'Product', required=True)
    quantity = fields.Float('Quantity', digits=(16, 4), required=True)
    weight = fields.Float('Weight', digits=(16, 4), required=True)
    party = fields.Many2One('party.party', 'Party', required=True)
    cost_price = fields.Numeric('Cost', digits=(16, 6), required=True)
    move = fields.Many2One('stock.move', 'Move')
    shipment = fields.Many2One('stock.shipment.out', 'Shipment')


    @fields.depends('product', 'category','cost_price')
    def on_change_product(self):
        if not self.product:
            return
        self.category = self.product.scrap_category
        self.cost_price = (self.product.template and
            self.product.template.scrap_category.cost_price)
        self.party = (self.product.template.scrap_category and
            self.product.template.scrap_category.party)

    @fields.depends('quantity', 'product')
    def on_change_with_weight(self, name=None):
        if not self.product:
            return None
        weight = self.product.template.weight
        return self.quantity * weight

class ScrapLine(ModelSQL, ModelView, ScrapMixin):
    'Scrap Line'
    __name__ = 'scrap.line'


class ScrapShipment(ModelSQL, ModelView, ScrapMixin):
    'Scrap Shipment'
    __name__ = 'scrap.shipment'

    @classmethod
    def table_query(cls):
        pool = Pool()
        Shipment = pool.get('stock.shipment.out')
        Scrap = pool.get('scrap.line')

        shipment = Shipment.__table__()
        scrap = Scrap.__table__()

        cursor = Transaction().connection.cursor()
        cursor.execute(*shipment.select(Max(shipment.id)))
        max_id, = cursor.fetchone()
        id_padding = 10 ** len(str(max_id))
        query = scrap.select(
                scrap.product,
                scrap.category,
                Sum(scrap.quantity).as_('quantity'),
                Sum(scrap.weight).as_('weight'),
                    (scrap.shipment + Literal(id_padding) +
                    scrap.product).as_('id'),
                scrap.shipment,
                Max(scrap.write_uid).as_('write_uid'),
                Max(scrap.create_uid).as_('create_uid'),
                Max(scrap.write_date).as_('write_date'),
                Max(scrap.create_date).as_('create_date'),
                Max(scrap.cost_price).as_('cost_price'),
                Literal(None).as_('move'),
                scrap.party,
                group_by=(scrap.product, scrap.category, scrap.shipment,
                    scrap.party)
        )
        print(query)

        return query





