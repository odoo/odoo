from odoo import models, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.onchange('country_id', 'currency_id')
    def _onchange_l10n_mx_currency(self):
        for company in self:
            if company.country_id.code == 'MX' and company.currency_id.name != 'MXN':
                return {
                    'warning': {
                        'title': _("Warning"),
                        'message': _("For Mexico, the currency should be MXN.")
                    }
                }
