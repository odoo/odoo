import io
from collections import defaultdict

from odoo import api, fields, models
from odoo.tools import format_date, pdf
from odoo.tools.pdf import DependencyError, OdooPdfFileReader, OdooPdfFileWriter, PdfReadError


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        # OVERRIDE Group all expenses per logical group, we want a concatenation of expenses per company, employee, payment_mode
        if self._get_report(report_ref).report_name != 'hr_expense.report_expense' or not res_ids:
            return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)

        # Prepare the reused data for the report and attachments
        all_expenses = self.env['hr.expense'].browse(res_ids)
        payment_mode_name_map = self._hr_expense_get_payment_mode_name_map()

        attachments_per_expense_id = dict(self.env['ir.attachment']._read_group(
            domain=[('res_id', 'in', res_ids), ('res_model', '=', 'hr.expense')],
            groupby=['res_id'],
            aggregates=['id:recordset'],
        ))

        collected_streams = {}
        idx = 0

        data = data or {}
        for expenses_per_employee in all_expenses.grouped('employee_id').values():
            exp_per_emp_per_mode = expenses_per_employee.grouped(lambda exp: payment_mode_name_map[exp.payment_mode])
            for payment_mode_str, expenses in exp_per_emp_per_mode.items():
                # Prepare header and footer and render the report (without attachments)
                data['general_info'] = self._hr_expense_get_general_info(
                    expenses,
                    payment_mode_str,
                )

                res = super()._render_qweb_pdf_prepare_streams(report_ref, data, expenses.ids)

                # Add the attachments to the report
                stream_id = len(expenses) == 1 and expenses.id
                stream_list = [res[stream_id]['stream']]
                expense_report = OdooPdfFileReader(stream_list[0], strict=False)
                output_pdf = OdooPdfFileWriter()
                output_pdf.append_pages_from_reader(expense_report)
                for expense in expenses:
                    # Get the attachment render streams and attach it as a new page to the report stream, grouped by expenses
                    attachments = attachments_per_expense_id.get(expense.id, self.env['ir.attachment'])
                    for attachment in self._prepare_local_attachments(attachments):
                        if attachment.mimetype == 'application/pdf':
                            attachment_stream = pdf.to_pdf_stream(attachment)
                        else:
                            # In case the attachment is not a pdf we will create a new PDF from the template "report_expense_img"
                            # And then append to the stream. By doing so, the attachment is put on a new page with the name of the expense
                            # associated to the attachment
                            attachment_prep_stream = super()._render_qweb_pdf_prepare_streams(
                                report_ref='hr_expense.report_expense_img',
                                data={**data, 'attachment': attachment},
                                res_ids=expense.ids,
                            )
                            attachment_stream = attachment_prep_stream[expense.id]['stream']
                        attachment_reader = OdooPdfFileReader(attachment_stream, strict=False)
                        try:
                            output_pdf.append_pages_from_reader(attachment_reader)
                        except (PdfReadError, DependencyError) as e:
                            expense._message_log(body=self.env._(
                                "The attachment (%(attachment_name)s) has not been added to the report due to the following "
                                "error: '%(error)s'",
                                attachment_name=attachment.name,
                                error=e
                            ))
                            continue
                        stream_list.append(attachment_stream)

                new_pdf_stream = io.BytesIO()
                output_pdf.write(new_pdf_stream)
                for stream in stream_list:
                    stream.close()
                collected_streams[idx] = {'stream': new_pdf_stream, 'attachment': None}
                idx += 1

        return collected_streams

    def _render_qweb_html(self, report_ref, docids, data=None):
        # OVERRIDE Group all expenses under one big report
        if self._get_report(report_ref).report_name != 'hr_expense.report_expense' or not docids:
            return super()._render_qweb_html(report_ref, docids, data)

        # Prepare the reused data for the report and attachments
        all_expenses = self.env['hr.expense'].browse(docids)
        payment_mode_name_map = self._hr_expense_get_payment_mode_name_map()

        # Prepare header and footer and render the report (without attachments)
        used_payment_mode = set(all_expenses.mapped('payment_mode'))
        if len(used_payment_mode) > 1:
            payment_mode = False
        else:
            payment_mode = used_payment_mode.pop()
        payment_mode_str = payment_mode_name_map[payment_mode]
        data = data or {}
        data['general_info'] = self._hr_expense_get_general_info(all_expenses, payment_mode_str)
        return super()._render_qweb_html(report_ref, docids, data)

    @api.model
    def _hr_expense_get_general_info(self, expenses, payment_mode_str):
        """ Helper method to collect all of the required data for the footer of the report

        :param :class:`~odoo.addons.hr_expense.models.hr_expense.HrExpense` expenses: The expenses to sum up
        :param str payment_mode_str: User-facing string for the expenses payment mode
        :return Footer data
        :rtype: dict
        """
        company_currency = expenses.company_currency_id[:1]  # Multi-company report makes no sense, so we don't care if the data is bad
        if len(set(expenses.mapped(lambda expense: expense.employee_id.id))) > 1:
            employee_name = self.env._("Multiple employees")
        elif not expenses.employee_id:
            employee_name = self.env._("No employee")
        else:
            employee_name = expenses.employee_id.name
        if len(set(expenses.mapped(lambda expense: expense.manager_id.id))) > 1:
            manager_name = self.env._("Multiple Managers")
        elif not expenses.manager_id:
            # We want to also catch auto-approved expenses that have no manager
            manager_name = self.env._("None (automatic)")
        else:
            manager_name = expenses.manager_id.name

        expenses_with_dates = expenses.filtered('date')
        date = max(expenses_with_dates.mapped('date')) if expenses_with_dates else fields.Date.context_today(self)

        return {
            'untaxed_amount': company_currency.format(sum(expenses.mapped('untaxed_amount'), start=0)),
            'tax_amount': company_currency.format(sum(expenses.mapped('tax_amount'), start=0)),
            'total_amount': company_currency.format(sum(expenses.mapped('total_amount'), start=0)),
            'date': format_date(self.env, date, lang_code=self.env.user.lang),
            'has_foreign_currency': bool(expenses.currency_id - company_currency),
            'manager_name': manager_name,
            'employee_name': employee_name,
            'payment_mode': payment_mode_str,
        }

    @api.model
    def _hr_expense_get_payment_mode_name_map(self):
        """ Helper to get the User facing strings for expenses payment mode

        :return: Mapping of technical -> user facing strings
        :rtype: defaultdict[str, str]
        """

        payment_mode_name_map = defaultdict(lambda: self.env._("Unknown"))
        payment_mode_name_map.update({
            **dict(self.env['hr.expense']._fields['payment_mode']._description_selection(self.env)),
            # If we add new ones, they would be present here
            'own_account': self.env._("Employee"),
            'company_account': self.env._("Company"),
            False: self.env._("Multiple payment modes"),
        })
        return payment_mode_name_map
