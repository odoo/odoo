# -*- coding: utf-8 -*-
from zlib import error as zlib_error

try:
    from PyPDF2.errors import PdfStreamError, PdfReadError
except ImportError:
    from PyPDF2.utils import PdfStreamError, PdfReadError

from odoo import api, models, _
from odoo.exceptions import UserError
from odoo.tools import pdf


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def retrieve_attachment(self, record):
        # get the original bills through the message_main_attachment_id field of the record
        if self.report_name == 'account.report_original_vendor_bill' and record.message_main_attachment_id:
            if record.message_main_attachment_id.mimetype == 'application/pdf' or \
               record.message_main_attachment_id.mimetype.startswith('image'):
                return record.message_main_attachment_id
        return super(IrActionsReport, self).retrieve_attachment(record)

    def _post_pdf(self, save_in_attachment, pdf_content=None, res_ids=None):
        # don't include the generated dummy report
        if self.report_name == 'account.report_original_vendor_bill':
            pdf_content = None
            res_ids = None
            if not save_in_attachment:
                raise UserError(_("No original vendor bills could be found for any of the selected vendor bills."))
        return super(IrActionsReport, self)._post_pdf(save_in_attachment, pdf_content=pdf_content, res_ids=res_ids)

    def _postprocess_pdf_report(self, record, buffer):
        # don't save the 'account.report_original_vendor_bill' report as it's just a mean to print existing attachments
        if self.report_name == 'account.report_original_vendor_bill':
            return None
        res = super(IrActionsReport, self)._postprocess_pdf_report(record, buffer)
        if self.model == 'account.move' and record.state == 'posted' and record.is_sale_document(include_receipts=True):
            attachment = self.retrieve_attachment(record)
            if attachment:
                attachment.register_as_main_attachment(force=False)
        return res

    def _render_qweb_pdf(self, res_ids=None, data=None):
        # Overridden so that the print > invoices actions raises an error
        # when trying to print a miscellaneous operation instead of an invoice.
        # + append context data with the display_name_in_footer parameter
        if self.model == 'account.move' and res_ids:
            invoice_reports = (self.env.ref('account.account_invoices_without_payment'), self.env.ref('account.account_invoices'))
            if self in invoice_reports:
                if self.env['ir.config_parameter'].sudo().get_param('account.display_name_in_footer'):
                    data = data and dict(data) or {}
                    data.update({'display_name_in_footer': True})
                moves = self.env['account.move'].browse(res_ids)
                if any(not move.is_invoice(include_receipts=True) for move in moves):
                    raise UserError(_("Only invoices could be printed."))

        return super()._render_qweb_pdf(res_ids=res_ids, data=data)

    def _retrieve_stream_from_attachment(self, attachment):
        # Overridden in order to add a banner in the upper right corner of the exported Vendor Bill PDF.
        stream = super()._retrieve_stream_from_attachment(attachment)
        vendor_bill_export = self.env.ref('account.action_account_original_vendor_bill')
        if self == vendor_bill_export and attachment.mimetype == 'application/pdf':
            record = self.env[attachment.res_model].browse(attachment.res_id)
            try:
                return pdf.add_banner(stream, record.name, logo=True)
            except (ValueError, PdfStreamError, PdfReadError, TypeError, zlib_error, NotImplementedError):
                record._message_log(body=_(
                    "There was an error when trying to add the banner to the original PDF.\n"
                    "Please make sure the source file is valid."
                ))
        return stream

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_tags(self):
        master_xmlids = [
            "account_invoices",
            "action_account_original_vendor_bill"
            "account_invoices_without_payment",
            "action_report_journal",
            "action_report_payment_receipt",
            "action_report_account_statement",
            "action_report_account_hash_integrity",
        ]
        for master_xmlid in master_xmlids:
            master_report = self.env.ref(f"account.{master_xmlid}", raise_if_not_found=False)
            if master_report and master_report in self:
                raise UserError(_("You cannot delete this report (%s), it is used by the accounting PDF generation engine.", master_report.name))
