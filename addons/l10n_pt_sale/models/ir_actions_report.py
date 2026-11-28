from odoo import models

# The templates of the sale order report, kept under one print per PT order.
SALE_ORDER_TEMPLATES = ('sale.report_saleorder', 'sale.report_saleorder_raw')


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _l10n_pt_sale_report_compliance(self, report_ref, res_ids):
        if self._is_sale_order_report(report_ref):
            # Keyed on each order's company, not the active one: a PT order printed while another
            # company is active is still issued in its own series. An order cancelled before it was
            # issued is no AT document, and prints as in any other country.
            orders = self.env['sale.order'].browse(res_ids).filtered(
                lambda o: o.country_code == 'PT' and o.l10n_pt_document_type,
            )
            if orders:
                self._l10n_pt_report_compliance(orders)

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        self._l10n_pt_sale_report_compliance(report_ref, res_ids)
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)

    def _render_qweb_html(self, report_ref, docids, data=None):
        # The portal's HTML view shows the issued order, so the order is issued first.
        self._l10n_pt_sale_report_compliance(report_ref, docids)
        return super()._render_qweb_html(report_ref, docids, data=data)

    def _l10n_pt_templates_with_print_version(self):
        return super()._l10n_pt_templates_with_print_version() + list(SALE_ORDER_TEMPLATES)

    def _render_template(self, template, values=None):
        # A PT order's print is kept under one template in `l10n.pt.attachment`, whichever renders it.
        if template in SALE_ORDER_TEMPLATES and any(
            order.country_code == 'PT' for order in (values or {}).get('docs') or ()
        ):
            template = SALE_ORDER_TEMPLATES[0]
        return super()._render_template(template, values)
