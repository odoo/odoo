from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _action_tax_report_error(self):
        self.ensure_one()
        if self.company_id.account_fiscal_country_id.code == 'FR':
            tax_report_exports = self.env['account.report.async.export'].search([
                ('report_id', '=', self.tax_closing_report_id.id),
                ('date_to', '=', self.date),
            ])
            return tax_report_exports._get_records_action()
        return super()._action_tax_report_error()
