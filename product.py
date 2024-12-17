from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool, PoolMeta


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


class ScrapLine(ModelSQL, ModelView):
    'Scrap Line'
    __name__ = 'scrap.line'

    product = fields.Many2One('product.product', 'Product', required=True)
    quantity = fields.Float('Quantity', digits=(16, 4), required=True)
    weight = fields.Float('Weight', digits=(16, 4), required=True)
    stock_move = fields.Many2One('stock.move', 'Stock Move')
    shipment = fields.Many2One('stock.shipment.out', 'Shipment Out')


class ScrapMixin():
    __slots__ = ()

    related_scrap_lines = fields.Function(fields.One2Many('scrap.line', None,
        'Scrap Lines'), 'get_related_scrap_lines')

    def get_related_scrap_lines(self, name):
        pool = Pool()
        ScrapLine = pool.get('scrap.line')

        if self.__name__ == 'stock.shipment.out':
            return ScrapLine.search([
                    ('shipment', '=', self.id),
                ])
        elif self.__name__ == 'account.invoice':
            return ScrapLine.search([
                ('invoice', '=', self.id),
                ])
