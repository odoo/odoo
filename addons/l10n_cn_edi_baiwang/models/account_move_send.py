# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    enable_l10n_cn_baiwang = fields.Boolean(compute='_compute_l10n_cn_baiwang_options')
    checkbox_l10n_cn_baiwang = fields.Boolean(
        string="Issue E-Fapiao (Baiwang)",
        compute='_compute_l10n_cn_baiwang_options',
        store=True,
        readonly=False,
    )

    @api.depends('move_ids')
    def _compute_l10n_cn_baiwang_options(self):
        for wizard in self:
            # Only enable if it's a Chinese invoice and hasn't been issued yet
            is_cn_invoice = any(m.country_code == 'CN' for m in wizard.move_ids)
            has_no_fapiao = any(not m.l10n_cn_fapiao_number for m in wizard.move_ids)

            if is_cn_invoice and has_no_fapiao:
                wizard.enable_l10n_cn_baiwang = True
                wizard.checkbox_l10n_cn_baiwang = True # Checked by default
            else:
                wizard.enable_l10n_cn_baiwang = False
                wizard.checkbox_l10n_cn_baiwang = False

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        """ Hook to trigger the API call before Odoo generates the PDF. """
        # Let Odoo do its standard processing first
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        # If our checkbox is ticked, execute the Baiwang logic
        if self.checkbox_l10n_cn_baiwang:
            for move, data in invoices_data.items():
                if move.country_code == 'CN' and not move.l10n_cn_fapiao_number:
                    move._l10n_cn_issue_fapiao()
