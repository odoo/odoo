from odoo import models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _default_closing_journal(self):
        if (self.env.company.account_fiscal_country_id.code or self.env.company.country_id.code) == 'CO':
            return self.env['account.journal']._ensure_company_closing_journal()
        return super()._default_closing_journal()
