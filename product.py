import math

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
    round_quantity = fields.Boolean('Round Quantity')

    @staticmethod
    def default_round_quantity():
        return False


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

    def _get_scrap_line(self, quantity):
        lines = []
        template = self.product.template
        scrap_line = ScrapLine()
        scrap_category = template.scrap_category
        scrap_line.category = scrap_category
        scrap_line.product = self.product
        if scrap_category.round_quantity:
            scrap_line.quantity = math.ceil(self.get_quantity() * quantity)
            scrap_line.weight = round(self.get_weight() * scrap_line.quantity, 4)
        else:
            scrap_line.quantity = round(self.get_quantity() * quantity, 4)
            scrap_line.weight = round(self.get_weight() * scrap_line.quantity, 4)

        scrap_line.party = template.scrap_category.party
        scrap_line.cost_price = template.scrap_category.cost_price
        lines.append(scrap_line)
        if not template.scrap_template_lines:
            return lines

        quantity = scrap_line.quantity
        for scrap_line in template.scrap_template_lines:
            lines += scrap_line._get_scrap_line(quantity)
        return lines


class ScrapProductMixin():
    __slots__ = ()

    scrap_category = fields.Many2One('scrap.category', 'Scrap Category')
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
    invoice_line = fields.Many2One('account.invoice.line', 'Invoice Line')
    invoice = fields.Many2One('account.invoice', 'Invoice')


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
        weight = self.product.template.weight or 0
        return (self.quantity or 0) * weight


class ScrapLine(ModelSQL, ModelView, ScrapMixin):
    'Scrap Line'
    __name__ = 'scrap.line'

    @classmethod
    def create(cls, vlist):
        lines = super().create(vlist)
        if not Transaction().context.get('explode_scrap', True):
            return lines

        new_lines = []
        for line in lines:
            for sline in line.product.template.scrap_template_lines:
                explodded = sline._get_scrap_line(line.quantity)
                for l in explodded:
                    l.shipment = line.shipment

                new_lines += explodded
        new_lines = super().create([l._save_values() for l in new_lines])
        return lines + new_lines


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
                    (scrap.shipment * Literal(id_padding) +
                    scrap.product).as_('id'),
                scrap.shipment,
                Max(scrap.write_uid).as_('write_uid'),
                Max(scrap.create_uid).as_('create_uid'),
                Max(scrap.write_date).as_('write_date'),
                Max(scrap.create_date).as_('create_date'),
                Max(scrap.cost_price).as_('cost_price'),
                Literal(None).as_('move'),
                Literal(None).as_('invoice_line'),
                Literal(None).as_('invoice'),
                scrap.party,
                group_by=(scrap.product, scrap.category, scrap.shipment,
                    scrap.party)
        )
        return query





