from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _l10n_pt_sale_report_compliance(self, report_ref, res_ids):
        if self._get_report(report_ref).report_name in ('sale.report_saleorder', 'sale.report_saleorder_raw'):
            # Keyed on each order's company, not the active one: a PT order printed while another
            # company is active is still issued in its own series.
            orders = self.env['sale.order'].browse(res_ids).filtered(lambda o: o.country_code == 'PT')
            if orders:
                self._l10n_pt_report_compliance('sale.order', orders.ids, compute_hash=True)

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        self._l10n_pt_sale_report_compliance(report_ref, res_ids)
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)

    def _render_qweb_html(self, report_ref, docids, data=None):
        # The portal's HTML view shows the issued order, so the order is issued first.
        self._l10n_pt_sale_report_compliance(report_ref, docids)
        return super()._render_qweb_html(report_ref, docids, data=data)

    def _l10n_pt_templates_with_print_version(self):
        return super()._l10n_pt_templates_with_print_version() + ['sale.report_saleorder', 'sale.report_saleorder_raw']

    def _render_template(self, template, values=None):
        if template in ('sale.report_saleorder', 'sale.report_saleorder_raw'):
            # Both templates should be saved under the same value in l10n_pt_attachment
            template = 'sale.report_saleorder'
        return super()._render_template(template, values)
