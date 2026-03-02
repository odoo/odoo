# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.model
    def _get_available_qr_methods(self):
        rslt = super()._get_available_qr_methods()
        if self.env.company.country_code == 'IN':
            rslt.append(('upi', _("UPI"), 10))
        return rslt

    def _get_qr_code_generation_params(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        # Nothing to do with the 'upi' method, we return None to avoid raising a NotImplementedError
        if qr_method == 'upi':
            return None
        return super()._get_qr_code_generation_params(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)
