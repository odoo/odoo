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
