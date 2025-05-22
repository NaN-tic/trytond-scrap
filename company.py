from trytond.model import fields
from trytond.pool import PoolMeta


class Company(metaclass=PoolMeta):
    __name__ = 'company.company'
    scrap_message = fields.Text('Scrap Message', translate=True)
