# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import _

from odoo.http import request, route, Controller, content_disposition


class HrEmployeeCV(Controller):

    @route(["/print/cv"], type='http', auth='user')
    def print_employee_cv(self, employee_ids='', color_primary='#666666', color_secondary='#666666', **post):
        if not request.env.user._is_internal() or not employee_ids or re.search("[^0-9|,]", employee_ids):
            return request.not_found()

        ids = [int(s) for s in employee_ids.split(',')]
        employees = request.env['hr.employee'].browse(ids)
        if not request.env.user.has_group('hr.group_hr_user') and employees.ids != request.env.user.employee_id.ids:
            return request.not_found()

        resume_type_education = request.env.ref('hr.resume_type_education', raise_if_not_found=False)
        skill_type_language = request.env.ref('hr.hr_skill_type_lang', raise_if_not_found=False)

        report = request.env.ref('hr.action_report_employee_cv', False)

        pdf_content, dummy = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            report, employees.ids, data={
            'color_primary': color_primary,
            'color_secondary': color_secondary,
            'resume_type_education': resume_type_education,
            'skill_type_language': skill_type_language,
            'show_skills': 'show_skills' in post,
            'show_contact': 'show_contact' in post,
            'show_others': 'show_others' in post,
        })

        if len(employees) == 1:
            report_name = _('Resume %s', employees.name)
        else:
            report_name = _('Resumes')

        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', content_disposition(report_name + '.pdf'))
        ]

        return request.make_response(pdf_content, headers=pdfhttpheaders)
