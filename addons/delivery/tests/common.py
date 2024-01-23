# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase


class DeliveryCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['delivery.carrier'].search([]).action_archive()
        cls.delivery_categ = cls.env.ref('delivery.product_category_deliveries')

        product = cls._prepare_carrier_product()
        cls.free_delivery = cls._prepare_carrier(product, fixed_price=0.0)
        cls.carrier = cls.free_delivery

    @classmethod
    def _prepare_carrier_product(cls, **values):
        default_values = {
            'name': "Carrier Product",
            'type': 'service',
            'categ_id': cls.delivery_categ.id,
            'sale_ok': False,
            'purchase_ok': False,
            'invoice_policy': 'order',
            'list_price': 5.0,
        }
        return cls.env['product.product'].create(dict(default_values, **values))

    @classmethod
    def _prepare_carrier(cls, product, **values):
        default_values = {
            'name': "Test Carrier",
            'fixed_price': 5.0,
            'delivery_type': 'fixed',
            'product_id': product.id,
        }
        return cls.env['delivery.carrier'].create(dict(default_values, **values))
