# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    # ─── Extra EDI Registration ─────────────────────────────────────────

    @api.model
    def _is_cn_baiwang_applicable(self, move):
        """Check if Baiwang EDI is applicable for this move."""
        return (
            move.country_code == 'CN'
            and move.move_type == 'out_invoice'
            and move.state == 'posted'
            and move.l10n_cn_baiwang_state not in ('issued', 'sent')
            and move.company_id.l10n_cn_baiwang_app_key
        )

    def _get_all_extra_edis(self):
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({
            'cn_baiwang': {
                'label': self.env._("by Baiwang (Issue E-Fapiao)"),
                'is_applicable': self._is_cn_baiwang_applicable,
                'help': self.env._("Submit the invoice to Baiwang for official Chinese e-Fapiao issuance."),
            },
        })
        return res

    # ─── Web Service Hook ───────────────────────────────────────────────

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            if 'cn_baiwang' not in invoice_data.get('extra_edis', set()):
                continue

            if error := invoice._l10n_cn_baiwang_issue_invoice():
                invoice_data['error'] = {
                    'error_title': self.env._("Error when issuing e-Fapiao via Baiwang:"),
                    'errors': [error],
                }

            if self._can_commit():
                self.env.cr.commit()
