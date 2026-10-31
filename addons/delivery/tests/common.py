# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.common import SaleCommon


class DeliveryCommon(SaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env["delivery.carrier"].search([]).action_archive()

        cls.free_delivery = cls._prepare_carrier(fixed_price=0.0)
        cls.carrier = cls.free_delivery

    @classmethod
    def _prepare_carrier(cls, **values):
        default_values = {"name": "Test Carrier", "fixed_price": 5.0, "delivery_type": "fixed"}
        return cls.env["delivery.carrier"].create(dict(default_values, **values))
