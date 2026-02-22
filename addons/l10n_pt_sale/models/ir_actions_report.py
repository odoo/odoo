from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        if (
            self._get_report(report_ref).report_name in ('sale.report_saleorder', 'sale.report_saleorder_raw')
            and self.env.company.account_fiscal_country_id.code == 'PT'
        ):
            self._l10n_pt_report_compliance('sale.order', res_ids, compute_hash=True, update_print_version=True)
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)

    def _l10n_pt_templates_with_print_version(self):
        return super()._l10n_pt_templates_with_print_version() + ['sale.report_saleorder', 'sale.report_saleorder_raw']

    def _render_template(self, template, values=None):
        if template in ('sale.report_saleorder', 'sale.report_saleorder_raw'):
            # Both templates should be saved under the same value in l10n_pt_attachment
            template = 'sale.report_saleorder'
        return super()._render_template(template, values)
