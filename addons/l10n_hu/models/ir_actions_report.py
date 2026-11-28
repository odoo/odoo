# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_html(self, report_ref, docids, data=None):
        # The Light layout is the one meant for letters: its recipient address fits the window of an envelope.
        # Print the Hungarian addresses there the way Magyar Posta asks for.
        report = self._get_report(report_ref)
        docs = self.env[report.model].sudo().browse(docids) if report.model in self.env else None
        companies = docs.company_id if docs is not None and 'company_id' in docs else self.env.company
        light_layout = self.env.ref('web.external_layout_standard', raise_if_not_found=False)
        if light_layout and (companies or self.env.company).external_report_layout_id == light_layout:
            self = self.with_context(l10n_hu_postal_address=True)
        return super()._render_qweb_html(report_ref, docids, data)
