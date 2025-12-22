import io
from odoo import models
from odoo.tools import pdf
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        # OVERRIDE
        res = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)
        if not res_ids:
            return res
        report = self._get_report(report_ref)
        if report.report_name == 'hr_expense.report_expense_sheet':
            expense_sheets = self.env['hr.expense.sheet'].browse(res_ids)
            for expense_sheet in expense_sheets:
                # Will contains the expense report
                stream_list = []
                stream = res[expense_sheet.id]['stream']
                stream_list.append(stream)
                attachments = self.env['ir.attachment'].search([('res_id', 'in', expense_sheet.expense_line_ids.ids), ('res_model', '=', 'hr.expense')])
                expense_report = OdooPdfFileReader(stream, strict=False)
                output_pdf = OdooPdfFileWriter()
                output_pdf.appendPagesFromReader(expense_report)
                for attachment in self._prepare_local_attachments(attachments):
                    if attachment.mimetype == 'application/pdf':
                        attachment_stream = pdf.to_pdf_stream(attachment)
                    else:
                        # In case the attachment is not a pdf we will create a new PDF from the template "report_expense_sheet_img"
                        # And then append to the stream. By doing so, the attachment is put on a new page with the name of the expense
                        # associated to the attachment
                        data['attachment'] = attachment
                        attachment_prep_stream = self._render_qweb_pdf_prepare_streams('hr_expense.report_expense_sheet_img', data, res_ids=res_ids)
                        attachment_stream = attachment_prep_stream[expense_sheet.id]['stream']
                    attachment_reader = OdooPdfFileReader(attachment_stream, strict=False)
                    output_pdf.appendPagesFromReader(attachment_reader)
                    stream_list.append(attachment_stream)

                new_pdf_stream = io.BytesIO()
                output_pdf.write(new_pdf_stream)
                res[expense_sheet.id]['stream'] = new_pdf_stream

                for stream in stream_list:
                    stream.close()
        return res
