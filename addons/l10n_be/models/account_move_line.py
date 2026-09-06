from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_default_taxes_on_vat_disabled(self):
        self.ensure_one()
        if self.move_id.country_code == 'BE':
            return self.company_id.account_sale_tax_id
        return super()._get_default_taxes_on_vat_disabled()
