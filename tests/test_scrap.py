import datetime
import unittest
from decimal import Decimal

from proteus import Model
from trytond.modules.account.tests.tools import create_chart, get_accounts
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.modules.currency.tests.tools import get_currency
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules, set_user


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):
        config = activate_modules('scrap')

        ProductTemplate = Model.get('product.template')
        ScrapCategory = Model.get('scrap.category')
        Party = Model.get('party.party')
        ProductUom = Model.get('product.uom')
        Sale = Model.get('sale.sale')

        today = datetime.date.today()

        # Create company::
        unit, = ProductUom.find([('name', '=', 'Unit')])
        eur = get_currency('EUR')
        _ = create_company(currency=eur)
        company = get_company()

        # set employee
        Employee = Model.get('company.employee')
        Party = Model.get('party.party')

        employee_party = Party(name="Employee")
        employee_party.save()
        employee = Employee(party=employee_party)
        employee.save()

        # Set user
        User = Model.get('res.user')
        user = User(config.user)
        user.employees.append(employee)
        user.employee = employee
        user.company = company
        user.save()
        set_user(user.id)

        # Get stock locations::
        Location = Model.get('stock.location')
        warehouse_location, = Location.find([('code', '=', 'WH')])
        warehouse_location.save()
        warehouse_location = warehouse_location

        customer = Party(name='Customer')
        customer.save()
        ecoembes = Party(name='Ecoembes')
        ecoembes.save()

        scrap_category = ScrapCategory(
            name='Paper',
            category='domestic',
            type_='single_use',
            party=ecoembes,
            cost_price=Decimal('0.01'),
            )
        scrap_category.save()


        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']

        # Create account category
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(
            name="Account Category",
            accounting=True,
            account_expense=expense,
            account_revenue=revenue,
            )
        account_category.save()

        template = ProductTemplate(
            name='box',
            default_uom=unit,
            type='goods',
            consumable=True,
            list_price=Decimal('0'),
            scrap_category=scrap_category,
            account_category=account_category,
        )
        template.save()
        box, = template.products

        box_template = ProductTemplate(
            name='individual box',
            default_uom=unit,
            type='goods',
            consumable=True,
            list_price=Decimal('10'),
            scrap_category=scrap_category,
            account_category=account_category,
        )
        box_template.save()
        individual_box, = box_template.products

        template = ProductTemplate(
            name='film box',
            default_uom=unit,
            type='goods',
            consumable=True,
            list_price=Decimal('10'),
            scrap_category=scrap_category,
            account_category=account_category,
        )
        template.save()
        film_box, = template.products
        scrap_line = box_template.scrap_template_lines.new()
        scrap_line.product = film_box
        scrap_line.quantity_formula = '1'
        scrap_line.weight_formula = '0.01'
        scrap_line.save()

        template = ProductTemplate(
            name='Product a',
            default_uom=unit,
            type='goods',
            salable=True,
            list_price=Decimal('10'),
            account_category=account_category,
        )
        scrap_line = template.scrap_template_lines.new()
        scrap_line.product = box
        scrap_line.quantity_formula = '1/30'
        scrap_line.weight_formula = '1/30'

        scrap_line = template.scrap_template_lines.new()
        scrap_line.product = individual_box
        scrap_line.quantity_formula = '1/24'
        scrap_line.weight_formula = '1/24'

        template.save()
        product_a, = template.products

        # Create sale of product_a
        sale = Sale(
            sale_date=today,
            shipment_party=customer,
            invoice_method='shipment',
            shipment_method='order',
            party=customer,
        )
        line = sale.lines.new()
        line.product = product_a
        line.quantity = 2
        line.unit_price = Decimal('10')
        sale.save()
        sale.click('quote')
        sale.click('confirm')
        sale.click('process')
        shipment, = sale.shipments

        shipment.click('assign_try')
        shipment.click('pick')
        shipment.click('pack')
        shipment.reload()
        move = shipment.outgoing_moves[0]
        self.assertEqual(move.product, product_a)
        self.assertEqual(move.quantity, 2)
        self.assertEqual(len(move.scrap_lines), 3)
        self.assertEqual(len(shipment.scrap_lines), 3)
        shipment.click('do')
        self.assertEqual(shipment.state, 'done')

        sale.reload()
        invoice, = sale.invoices
        self.assertEqual(len(invoice.related_scrap_lines), 3)
        self.assertEqual(invoice.scrap_amount, Decimal('0.0001'))
