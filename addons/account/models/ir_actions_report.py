# -*- coding: utf-8 -*-
import io

from collections import OrderedDict

from odoo import models, _
from odoo.exceptions import UserError


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, data, res_ids=None):
        # Custom behavior for 'account.report_original_vendor_bill'.
        if self.report_name != 'account.report_original_vendor_bill':
            return super()._render_qweb_pdf_prepare_streams(data, res_ids=res_ids)

        invoices = self.env['account.move'].browse(res_ids)
        if any(x.move_type not in ('in_invoice', 'in_receipt') for x in invoices):
            raise UserError(_("You can only print the original document for vendor bills."))

        original_attachments = invoices.message_main_attachment_id
        if not original_attachments:
            raise UserError(_("No original vendor bills could be found for any of the selected vendor bills."))

        collected_streams = OrderedDict()
        for invoice in invoices:
            if invoice.message_main_attachment_id:
                collected_streams[invoice.id] = {
                    'stream': io.BytesIO(invoice.message_main_attachment_id.raw),
                    'attachment': invoice.message_main_attachment_id,
                }
        return collected_streams

    def _render_qweb_pdf(self, res_ids=None, data=None):
        # Check for reports only available for invoices.
        if self.report_name in ('account.report_invoice_with_payments', 'account.report_invoice'):
            invoices = self.env['account.move'].browse(res_ids)
            if any(x.move_type == 'entry' for x in invoices):
                raise UserError(_("Only invoices could be printed."))

        return super()._render_qweb_pdf(res_ids=res_ids, data=data)
