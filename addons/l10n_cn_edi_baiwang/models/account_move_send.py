# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    enable_l10n_cn_baiwang = fields.Boolean(compute='_compute_l10n_cn_baiwang_options')
    checkbox_l10n_cn_baiwang = fields.Boolean(
        string="Issue E-Fapiao (Baiwang)",
        compute='_compute_l10n_cn_baiwang_options',
        store=True,
        readonly=False,
    )

    def _compute_l10n_cn_baiwang_options(self):
        for wizard in self:
            # Safely fetch the moves being processed regardless of single/batch wizard
            active_ids = self.env.context.get('active_ids', [])
            moves = self.env['account.move'].browse(active_ids)

            is_cn_invoice = any(m.country_code == 'CN' for m in moves)
            has_no_fapiao = any(not m.l10n_cn_fapiao_number for m in moves)

            if is_cn_invoice and has_no_fapiao:
                wizard.enable_l10n_cn_baiwang = True
                wizard.checkbox_l10n_cn_baiwang = True  # Checked by default
            else:
                wizard.enable_l10n_cn_baiwang = False
                wizard.checkbox_l10n_cn_baiwang = False

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        """ Hook to trigger the API call before Odoo generates the PDF. """
        # Let Odoo do its standard processing first (like Peppol or standard EDI)
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for move, data in invoices_data.items():
            # Check if Baiwang is the selected sending method for this customer
            # OR if our specific wizard checkbox was ticked.
            is_baiwang_method = move.partner_id.invoice_sending_method == 'baiwang'
            is_checkbox_ticked = getattr(self, 'checkbox_l10n_cn_baiwang', False)

            if is_baiwang_method or is_checkbox_ticked:
                # Execute only if it's a CN invoice and hasn't been issued yet
                if move.country_code == 'CN' and not move.l10n_cn_fapiao_number:
                    move._l10n_cn_issue_fapiao()
