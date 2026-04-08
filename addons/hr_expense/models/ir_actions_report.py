import io
from PIL import Image, ImageDraw, ImageFont

from odoo import models
from odoo.exceptions import UserError
from odoo.tools.image import binary_to_image
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _convert_image_attachment_to_pdf(self, attachment, expense_name):
        """
        Helper to safely convert an image attachment to a centered PDF page.
        """
        try:
            img = binary_to_image(attachment.raw).convert('RGB')
        except UserError:
            # Skip invalid/unreadable images without crashing the whole report
            return None

        a4_w, a4_h = 595, 842
        img.thumbnail((450, 650), Image.Resampling.LANCZOS)

        canvas_img = Image.new('RGB', (a4_w, a4_h), 'white')
        x_offset = int((a4_w - img.width) / 2)
        y_offset = 120
        canvas_img.paste(img, (x_offset, y_offset))

        draw = ImageDraw.Draw(canvas_img)

        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 32)
        except OSError:
            try:
                font = ImageFont.truetype("arial.ttf", 32)
            except OSError:
                font = ImageFont.load_default()

        title_text = expense_name or "Expense Receipt"

        try:
            text_w = draw.textlength(title_text, font=font)
        except AttributeError:
            text_w = 200

        text_x = int((a4_w - text_w) / 2) if text_w < a4_w else 40
        draw.text((text_x, 50), title_text, fill="black", font=font)

        attachment_stream = io.BytesIO()
        canvas_img.save(attachment_stream, format='PDF', resolution=72.0)
        attachment_stream.seek(0)

        return attachment_stream

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        report = self._get_report(report_ref)

        if not res_ids or report.report_name != 'hr_expense.report_expense':
            return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)

        expenses = self.env['hr.expense'].browse(res_ids)
        output_pdf = OdooPdfFileWriter()
        streams_to_close = []

        expenses = expenses.sorted(key=lambda e: (e.employee_id.name or '', e.payment_mode or ''))
        expense_groups = {}
        for expense in expenses:
            group_key = (expense.employee_id, expense.payment_mode)
            if group_key not in expense_groups:
                expense_groups[group_key] = self.env['hr.expense']
            expense_groups[group_key] += expense

        attachments_by_expense = dict(
            self.env['ir.attachment']._read_group(
                domain=[('res_id', 'in', expenses.ids), ('res_model', '=', 'hr.expense')],
                groupby=['res_id'],
                aggregates=['id:recordset'],
            )
        )

        for (employee, payment_mode), group_expenses in expense_groups.items():
            html = self._render_qweb_html('hr_expense.report_expense_summary', group_expenses.ids, data=data)[0]

            summary_pdf_content, _html_ids = self._run_pdf_engine('wkhtmltopdf', html, report_ref=report)

            summary_stream = io.BytesIO(summary_pdf_content)
            output_pdf.append_pages_from_reader(OdooPdfFileReader(summary_stream, strict=False))
            streams_to_close.append(summary_stream)

            for expense in group_expenses:
                attachments = attachments_by_expense.get(expense.id, self.env['ir.attachment'])

                for attachment in self._prepare_local_attachments(attachments):
                    try:
                        if attachment.mimetype == 'application/pdf':
                            attachment_stream = io.BytesIO(attachment.raw)
                            reader = OdooPdfFileReader(attachment_stream, strict=False)

                            for i in range(len(reader.pages)):
                                page = reader.pages[i]

                                try:
                                    w = float(page.mediabox[2] - page.mediabox[0])
                                    h = float(page.mediabox[3] - page.mediabox[1])
                                    max_w, max_h = 595.0, 842.0

                                    if w > max_w or h > max_h:
                                        factor = min(max_w / w, max_h / h)
                                        try:
                                            page.scale_by(factor)
                                        except AttributeError:
                                            page.scaleBy(factor)

                                        page.mediabox.upper_right = (
                                            float(page.mediabox[0]) + (w * factor),
                                            float(page.mediabox[1]) + (h * factor)
                                        )
                                except (AttributeError, ValueError, TypeError):
                                    pass

                                try:
                                    output_pdf.add_page(page)
                                except AttributeError:
                                    output_pdf.addPage(page)

                            streams_to_close.append(attachment_stream)

                        elif attachment.mimetype.startswith('image/'):
                            img_stream = self._convert_image_attachment_to_pdf(attachment, expense.name)
                            if img_stream:
                                output_pdf.append_pages_from_reader(OdooPdfFileReader(img_stream, strict=False))
                                streams_to_close.append(img_stream)
                        else:
                            continue

                    except (OSError, ValueError, TypeError) as e:
                        expense._message_log(body=self.env._(
                            "The attachment (%(attachment_name)s) has not been added to the report due to: '%(error)s'",
                            attachment_name=attachment.name,
                            error=e,
                        ))

        new_pdf_stream = io.BytesIO()
        output_pdf.write(new_pdf_stream)

        res = {expense_id: {'stream': None} for expense_id in res_ids}
        res[res_ids[0]]['stream'] = new_pdf_stream

        for stream in streams_to_close:
            stream.close()

        return res
