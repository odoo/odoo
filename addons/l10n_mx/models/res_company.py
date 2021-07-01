from odoo import models, api, _
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.constrains('country_id', 'currency_id')
    def _mx_company_currency(self):
        for company in self:
            if company.country_id.code == 'MX' and company.currency_id.name != 'MXN':
                raise UserError(_('Mexican companies must have Mexican Peso as their currency.'))
