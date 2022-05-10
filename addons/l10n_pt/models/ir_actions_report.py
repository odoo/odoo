from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf(self, res_ids=None, data=None):
        self_sudo = self.sudo()
        model = self_sudo.model
        if model != "account.move":
            return super()._render_qweb_pdf(res_ids, data)
        record = self.env[model].browse(res_ids)
        if record.company_id.account_fiscal_country_id.code != "PT":
            return super()._render_qweb_pdf(res_ids, data)
        if not record.l10n_pt_duplicate_pdf:
            # Create original and duplicate PDFs but return original one
            original = super()._render_qweb_pdf(record.ids)[0]
            record.l10n_pt_duplicate_pdf = original  # Set to something other than False to let XML report know it should show "Duplicate" instead of "Original"
            record.l10n_pt_duplicate_pdf = super()._render_qweb_pdf(record.ids)[0]
            return original, 'pdf'
        return record.l10n_pt_duplicate_pdf, 'pdf'

    # TODO: test with multiple invoices
