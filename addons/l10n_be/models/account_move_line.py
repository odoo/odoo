from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _compute_tax_ids(self):
        move_lines_to_update = self.filtered(
            lambda line: line.move_id.country_code == 'BE' and line.move_id.company_vat_disabled
        )
        for line in move_lines_to_update:
            line.tax_ids = line.move_id.company_id.account_sale_tax_id.ids
        super(AccountMoveLine, self - move_lines_to_update)._compute_tax_ids()
