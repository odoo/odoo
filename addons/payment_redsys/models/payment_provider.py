# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.payment_redsys import const


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('redsys', 'Redsys')],
        ondelete={'redsys': 'set default'}
    )
    redsys_merchant_code = fields.Char(string='Redsys Merchant Code', required_if_provider='redsys')
    redsys_merchant_terminal = fields.Char(string='Redsys Merchant Terminal')
    redsys_secret_key = fields.Char(
        string='Redsys Secret Key',
        required_if_provider='redsys',
        groups='base.group_system',
    )

    def _redsys_get_api_url(self):
        if self.state == 'enabled':
            return 'https://sis.redsys.es/sis/realizarPago'
        else:  # 'test'
            return 'https://sis-t.redsys.es:25443/sis/realizarPago'

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'redsys':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES
