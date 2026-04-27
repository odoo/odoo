# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_booking_fee = fields.Boolean(compute='_compute_is_booking_fee', compute_sudo=True)

    def _compute_is_booking_fee(self):
        service_products = self.filtered(lambda pp:
            pp.type == 'service'
            and pp.sale_ok
            and pp.service_tracking == 'no'
        )
        (self - service_products).is_booking_fee = False
        if not service_products:
            return
        has_appointment_type_per_product = {
            product.id: bool(count)
            for product, count in self.env['appointment.type']._read_group(
                domain=[
                    ('has_payment_step', '=', True),
                    ('product_id', 'in', service_products.ids),
                ],
                groupby=['product_id'],
                aggregates=['__count'],
            )
        }
        for product in service_products:
            product.is_booking_fee = has_appointment_type_per_product.get(product.id, False)
