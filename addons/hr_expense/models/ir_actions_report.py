import io

from odoo import _, fields, models
from odoo.tools import pdf
from odoo.tools.pdf import DependencyError, OdooPdfFileReader, OdooPdfFileWriter, PdfReadError


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        # OVERRIDE
        if self._get_report(report_ref).report_name != 'hr_expense.report_expense' or not res_ids:
            return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)

        # Prepare the reused data for the report and attachments
        all_expenses = self.env['hr.expense'].browse(res_ids)
        payment_mode_name_map = {
            'own_account': self.env._("Employee"),
            'company_account': self.env._("Company"),
            'payslip': self.env._("Employee"),
        }
        multiple_manager_name = self.env._("Multiple Managers")
        no_manager_name = self.env._("None (automatic)")
        all_attachments = self.env['ir.attachment'].search([('res_id', 'in', res_ids), ('res_model', '=', 'hr.expense')])

        collected_streams = {}
        for idx, expenses_per_employee in enumerate(all_expenses.grouped('employee_id').values()):
            for payment_mode, expenses in expenses_per_employee.grouped('payment_mode').items():
                # Basically we want a concatenation of expenses per company, employee, payment_mode

                # Prepare header and footer and render the report (without attachments)
                company_currency = expenses.company_currency_id
                if len(expenses.manager_id) > 1:
                    # We want to also catch auto-approved expenses that have no manager
                    manager_name = multiple_manager_name
                elif not expenses.manager_id:
                    manager_name = no_manager_name
                else:
                    manager_name = expenses.manager_id.name
                data['general_info'] = {
                    'untaxed_amount': company_currency.format(sum(expenses.mapped('untaxed_amount'), start=0)),
                    'tax_amount': company_currency.format(sum(expenses.mapped('tax_amount'), start=0)),
                    'total_amount': company_currency.format(sum(expenses.mapped('total_amount'), start=0)),
                    'date': max(expenses.mapped('date')) if expenses else fields.Date.context_today(self),
                    'has_foreign_currency': bool(expenses.currency_id - company_currency),
                    'manager_name': manager_name,
                    'employee_name': expenses.employee_id.name,
                    'payment_mode': payment_mode_name_map[payment_mode],
                }

                res = super()._render_qweb_pdf_prepare_streams(report_ref, data, expenses.ids)

                # Add the attachments to the report
                stream_id = False if len(expenses) > 1 else expenses.id
                stream_list = [res[stream_id]['stream']]
                expense_report = OdooPdfFileReader(stream_list[0], strict=False)
                output_pdf = OdooPdfFileWriter()
                output_pdf.append_pages_from_reader(expense_report)
                for expense in self.env['hr.expense'].browse(expenses.ids).with_prefetch(res_ids):
                    # Get the attachment render streams and attach it as a new page to the report stream, grouped by expenses
                    attachments = (
                        all_attachments.filtered(lambda att: att.res_id == expense.id)
                        .with_prefetch(all_attachments.ids)
                    )
                    for attachment in self._prepare_local_attachments(attachments):
                        if attachment.mimetype == 'application/pdf':
                            attachment_stream = pdf.to_pdf_stream(attachment)
                        else:
                            # In case the attachment is not a pdf we will create a new PDF from the template "report_expense_img"
                            # And then append to the stream. By doing so, the attachment is put on a new page with the name of the expense
                            # associated to the attachment
                            attachment_prep_stream = self._render_qweb_pdf_prepare_streams(
                                report_ref='hr_expense.report_expense_img',
                                data={**data, 'attachment': attachment},
                                res_ids=expense.ids,
                            )
                            attachment_stream = attachment_prep_stream[expense.id]['stream']
                        attachment_reader = OdooPdfFileReader(attachment_stream, strict=False)
                        try:
                            output_pdf.append_pages_from_reader(attachment_reader)
                        except (PdfReadError, DependencyError) as e:
                            expense._message_log(body=_(
                                "The attachment (%(attachment_name)s) has not been added to the report due to the following error: '%(error)s'",
                                attachment_name=attachment.name,
                                error=e
                            ))
                            continue
                        stream_list.append(attachment_stream)

                new_pdf_stream = io.BytesIO()
                output_pdf.write(new_pdf_stream)
                collected_streams[idx] = {'stream': new_pdf_stream, 'attachment': None}
        return collected_streams
