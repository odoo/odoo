import re

from odoo.http import Controller, prepare_content_disposition_header, request, route
from odoo.libs.debug_log import DebugLog

EMPLOYEE_IDS_RE = re.compile(r"^[0-9]+(,[0-9]+)*$")
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
DEFAULT_COLOR = "#666666"

_debug = DebugLog(__name__)


class HrEmployeeCV(Controller):
    def _printable_employees(self, employee_ids):
        if not (isinstance(employee_ids, str) and EMPLOYEE_IDS_RE.match(employee_ids)):
            _debug.logic("cv_ids_rejected", raw=isinstance(employee_ids, str))
            return request.env["hr.employee"]
        return request.env["hr.employee"]._get_cv_printable_employees(
            [int(employee_id) for employee_id in employee_ids.split(",")]
        )

    @staticmethod
    def _css_color(color):
        return (
            color if isinstance(color, str) and COLOR_RE.match(color) else DEFAULT_COLOR
        )

    @route(["/print/cv"], type="http", auth="user")
    def print_employee_cv(
        self,
        employee_ids="",
        color_primary=DEFAULT_COLOR,
        color_secondary=DEFAULT_COLOR,
        **post,
    ):
        employees = self._printable_employees(employee_ids)
        if not employees:
            _debug.logic("cv_print_not_found", user=request.env.user)
            return request.prepare_not_found_error()

        resume_type_education = request.env.ref(
            "hr_skills.resume_type_education", raise_if_not_found=False
        )
        skill_type_language = request.env.ref(
            "hr_skills.hr_skill_type_lang", raise_if_not_found=False
        )

        report = request.env.ref("hr_skills.action_report_employee_cv", False)

        pdf_content, _content_type = (
            request.env["ir.actions.report"]
            .sudo()
            ._render_qweb_pdf(
                report,
                employees.ids,
                data={
                    "color_primary": self._css_color(color_primary),
                    "color_secondary": self._css_color(color_secondary),
                    "resume_type_education": resume_type_education,
                    "skill_type_language": skill_type_language,
                    "show_skills": "show_skills" in post,
                    "show_contact": "show_contact" in post,
                    "show_others": "show_others" in post,
                },
            )
        )

        _debug.perf.count(
            "cv_pdf_rendered", employees=employees, bytes=len(pdf_content)
        )
        if len(employees) == 1:
            report_name = request.env._("Resume %s", employees.name)
        else:
            report_name = request.env._("Resumes")

        pdfhttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(pdf_content)),
            (
                "Content-Disposition",
                prepare_content_disposition_header(report_name + ".pdf"),
            ),
        ]

        return request.prepare_response(pdf_content, headers=pdfhttpheaders)
