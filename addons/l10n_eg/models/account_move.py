from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    narration = fields.Html(translate=True)

    def _get_name_invoice_report(self):
        # EXTENDS account
        self.ensure_one()
        if self.company_id.country_code == 'EG' and self.company_id.l10n_eg_dual_language_invoice:
            return 'l10n_eg.l10n_eg_report_invoice_document'
        return super()._get_name_invoice_report()
