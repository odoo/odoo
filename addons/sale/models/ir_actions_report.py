from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        # EXTENDS base
        collected_streams = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)

        if collected_streams \
                and res_ids \
                and len(res_ids) == 1 \
                and self._is_sale_order_report(report_ref):
            sale_order = self.env['sale.order'].browse(res_ids)
            return self._embed_edi_attachments(sale_order, collected_streams)

        return collected_streams

    def _is_sale_order_report(self, report_ref):
        return self._get_report(report_ref).report_name in (
            'sale.report_saleorder_document',
            'sale.report_saleorder',
        )
