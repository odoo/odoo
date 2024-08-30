# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResBank(models.Model):
    _inherit = 'res.bank'

    def _get_fiscal_country_codes(self):
        return ','.join(self.env.companies.account_fiscal_country_id.mapped('code'))

    l10n_cl_sbif_code = fields.Char('Cod. SBIF', size=10)
    fiscal_country_codes = fields.Char(store=False, default=_get_fiscal_country_codes)
