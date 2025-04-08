from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        # EXTENDS base
        collected_streams = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)

        if collected_streams \
                and res_ids \
                and len(res_ids) == 1 \
                and self._is_purchase_order_report(report_ref):
            purchase_order = self.env['purchase.order'].browse(res_ids)
            builders = purchase_order._get_edi_builders()

            if len(builders) == 0:
                return collected_streams

            return self._embed_edi_attachments(purchase_order, collected_streams, builders)

        return collected_streams

    def _is_purchase_order_report(self, report_ref):
        return self._get_report(report_ref).report_name in (
            'purchase.report_purchasequotation',
            'purchase.report_purchaseorder'
        )
