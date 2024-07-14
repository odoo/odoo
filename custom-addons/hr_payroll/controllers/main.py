# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import re

from PyPDF2 import PdfFileReader, PdfFileWriter

from odoo.http import request, route, Controller, content_disposition
from odoo.tools.safe_eval import safe_eval


class HrPayroll(Controller):

    @route(["/print/payslips"], type='http', auth='user')
    def get_payroll_report_print(self, list_ids='', **post):
        if not request.env.user.has_group('hr_payroll.group_hr_payroll_user') or not list_ids or re.search("[^0-9|,]", list_ids):
            return request.not_found()

        ids = [int(s) for s in list_ids.split(',')]
        payslips = request.env['hr.payslip'].browse(ids)

        pdf_writer = PdfFileWriter()
        payslip_reports = payslips._get_pdf_reports()

        for report, slips in payslip_reports.items():
            for payslip in slips:
                pdf_content, _ = request.env['ir.actions.report'].\
                    with_context(lang=payslip.employee_id.lang or payslip.env.lang).\
                    sudo().\
                    _render_qweb_pdf(report, payslip.id, data={'company_id': payslip.company_id})
                reader = PdfFileReader(io.BytesIO(pdf_content), strict=False, overwriteWarnings=False)

                for page in range(reader.getNumPages()):
                    pdf_writer.addPage(reader.getPage(page))

        _buffer = io.BytesIO()
        pdf_writer.write(_buffer)
        merged_pdf = _buffer.getvalue()
        _buffer.close()

        if len(payslip_reports) == 1 and len(payslips) == 1 and payslips.struct_id.report_id.print_report_name:
            report_name = safe_eval(payslips.struct_id.report_id.print_report_name, {'object': payslips})
        else:
            report_name = ' - '.join(r.name for r in list(payslip_reports.keys()))
            employees = payslips.employee_id.mapped('name')
            if len(employees) == 1:
                report_name = '%s - %s' % (report_name, employees[0])

        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(merged_pdf)),
            ('Content-Disposition', content_disposition(report_name + '.pdf'))
        ]

        return request.make_response(merged_pdf, headers=pdfhttpheaders)

    @route(["/get_payroll_warnings"], type="json", auth='user')
    def get_payroll_warning_data(self):
        return request.env['hr.payslip']._get_dashboard_warnings()
