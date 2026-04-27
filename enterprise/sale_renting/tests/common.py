# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo import Command, fields

from odoo.addons.sale.tests.common import SaleCommon


class SaleRentingCommon(SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        Recurrence = cls.env['sale.temporal.recurrence']
        cls.recurrence_hour = Recurrence.create({'duration': 1, 'unit': 'hour'})
        cls.recurrence_day = Recurrence.create({'duration': 1, 'unit': 'day'})

    @classmethod
    def _create_product(cls, **kwargs):
        if 'rent_ok' not in kwargs:
            kwargs['rent_ok'] = True
        return super()._create_product(**kwargs)

    @classmethod
    def _create_rental_order(cls, days):
        rental_product = cls._create_product(
            product_pricing_ids=[
                Command.create({'recurrence_id': cls.recurrence_day.id, 'price': 100})
            ]
        )
        start_date = fields.Datetime.now().replace(hour=0, minute=0, second=0)
        return_date = start_date + timedelta(days=days, seconds=-1)
        return cls.env['sale.order'].with_context(in_rental_app=True).create({
            'partner_id': cls.partner.id,
            'rental_start_date': start_date,
            'rental_return_date': return_date,
            'order_line': [Command.create({'product_id': rental_product.id})]
        })
