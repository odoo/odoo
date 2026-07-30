# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import models
from odoo.tools.business_data import mod10r


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _get_alerts(self):
        alerts = super()._get_alerts()
        for payment in self:
            if payment.payment_type == 'outbound' and\
                    payment.partner_id.country_code in ['CH', 'LI'] and\
                    payment.partner_bank_id.l10n_ch_qr_iban and\
                    not payment._l10n_ch_reference_is_valid(payment.memo):
                alerts['l10n_ch_reference_warning'] = {
                    'message': self.env._("Please fill in a correct QRR reference in the payment reference. The banks will refuse your payment file otherwise."),
                    'level': 'warning',
                }
        return alerts

    def _l10n_ch_reference_is_valid(self, payment_reference):
        """Check if this invoice has a valid reference (for Switzerland)
        e.g.
        000000000000000000000012371
        210000000003139471430009017
        21 00000 00003 13947 14300 09017
        """
        self.ensure_one()
        if not payment_reference:
            return False
        ref = payment_reference.replace(' ', '')
        if re.match(r'^(\d{2,27})$', ref):
            return ref == mod10r(ref[:-1])
        return False
