# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.const import REPORT_REASONS_MAPPING


class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    def _get_compatible_payment_methods(
        self,
        *args,
        report=None,
        invoice_id=None,
        sale_order_id=None,
        **kwargs
    ):
        """ Override of `payment` to remove `zip` from payment methods if no address is given. """
        payment_methods = super()._get_compatible_payment_methods(
            *args, report=report, invoice_id=invoice_id, sale_order_id=sale_order_id, **kwargs
        )
        payment_method_zip = self.env['payment.method'].search([('code', '=', 'zip')])
        if payment_method_zip and not (invoice_id or sale_order_id):
            payment_methods -= payment_method_zip
            payment_utils.add_to_report(
                report,
                payment_method_zip,
                available=False,
                reason=REPORT_REASONS_MAPPING['require_delivery_address'],
            )
        return payment_methods
