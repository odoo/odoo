# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        # OVERRIDE
        res = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)
        if not res_ids:
            return res
        report = self._get_report(report_ref)
        if report.report_name in ('account.report_invoice_with_payments', 'account.report_invoice'):
            invoices = self.env[report.model].browse(res_ids)
            if invoices.company_id.account_fiscal_country_id.code == 'PT':
                invoices.l10n_pt_account_compute_missing_hashes(invoices.company_id.id)
                res = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)
        return res
