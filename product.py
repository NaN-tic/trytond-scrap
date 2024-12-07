from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import PoolMeta


class ScrapCategory(ModelSQL, ModelView):
    'Scrap Category'
    __name__ = 'scrap.category'

    name = fields.Char('Name', required=True)
    scrap_category = fields.Selection(
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


class ScraplineTemplate(ModelSQL, ModelView):
    'Scrap Template Line'
    __name__ = 'scrap.template.line'

    template = fields.Many2One('product.template', 'Template', required=True)
    scrap_product = fields.Many2One('product.product', 'Scrap   Product',
        required=True)
    quantity_formula = fields.Char('Quantity Formula', required=True)
    weight_formula = fields.Char('Weight Formula', required=True)


class ScrapMixin():
    __slots__ = ()

    scrap_category = fields.Many2One('scrap.category', 'Scrap Category')
    scrap_package = fields.Boolean('Scrap Package')
    scrap_type = fields.Selection(
        [('single_use', 'Single Use'),
         ('reusable', 'Reusable'),
         ('both', 'Both')],
        'Scrap Type', )
    scrap_template_lines = fields.One2Many('scrap.template.line', 'template',
        'Scrap Lines')


class ProductTemplate(ScrapMixin, metaclass=PoolMeta):
    __name__ = 'product.template'


class ScrapLine(ModelSQL, ModelView):
    'Scrap Line'
    __name__ = 'scrap.line'

    scrap_product = fields.Many2One('product.product', 'Product', required=True)
    quantity = fields.Float('Quantity', required=True)
    weight = fields.Float('Weight', required=True)
    origin = fields.Reference('Origin', selection='get_origin')

    @staticmethod
    def get_origin():
        return [('stock.move', 'Stock Move'),
                ('stock.shipment.out', 'Shipment Out')]


class StockShipmentOut(metaclass=PoolMeta):
    __name__ = 'stock.shipment.out'

    scrap_lines = fields.Function(fields.One2Many('scrap.line', None,
            'Scrap Lines'), 'get_scrap_lines')

    def get_scrap_lines(self, name):
        res = []
        for line in self.moves:
            res.extend(line.scrap_lines)
        return res


class StockMove(metaclass=PoolMeta):
    __name__ = 'stock.move'

    scrap_lines = fields.One2Many('scrap.line', 'origin', 'Scrap Lines')
