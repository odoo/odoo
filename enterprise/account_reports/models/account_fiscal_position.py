from odoo import models


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    def _inverse_foreign_vat(self):
        # EXTENDS account
        super()._inverse_foreign_vat()
        for fpos in self:
            if fpos.foreign_vat:
                fpos._create_draft_closing_move_for_foreign_vat()

    def _create_draft_closing_move_for_foreign_vat(self):
        self.ensure_one()
        existing_draft_closings = self.env['account.move'].search([('tax_closing_report_id', '!=', False), ('state', '=', 'draft')])
        for closing_date, entries in existing_draft_closings.grouped('date').items():
            for entry in entries:
                self.company_id._get_and_update_tax_closing_moves(closing_date, entry.tax_closing_report_id, fiscal_positions=self)
