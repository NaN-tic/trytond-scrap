# This file is part trytond-scrap module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool

from . import invoice, product, shipment


def register():
    Pool.register(
        invoice.Invoice,
        invoice.ScrapInvoice,
        product.Company,
        product.ScrapCategory,
        product.ScraplineTemplate,
        product.ProductTemplate,
        product.ScrapLine,
        product.ScrapShipment,
        shipment.ShipmentOut,
        shipment.StockMove,
        module='scrap', type_='model')
    Pool.register(
        module='scrap', type_='wizard')
    Pool.register(
        module='scrap', type_='report')
