import re

from odoo.http import Controller, prepare_content_disposition_header, request, route

EMPLOYEE_IDS_RE = re.compile(r"^[0-9]+(,[0-9]+)*$")
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
DEFAULT_COLOR = "#666666"


class HrEmployeeCV(Controller):
    def _printable_employees(self, employee_ids):
        """The employees the current user may print, or an empty recordset.

        An HR user prints whichever employees they can read; anyone else prints
        only themself. The rendering below runs as superuser, so this is the
        only access check the report gets.
        """
        user = request.env.user
        if not user._is_internal() or not (
            isinstance(employee_ids, str) and EMPLOYEE_IDS_RE.match(employee_ids)
        ):
            return request.env["hr.employee"]
        ids = [int(s) for s in employee_ids.split(",")]
        employees = request.env["hr.employee"].browse(ids).exists()
        if len(employees) != len(set(ids)):
            return request.env["hr.employee"]
        if user.has_group("hr.group_hr_user"):
            return employees if employees.has_access("read") else employees.browse()
        return employees if employees == user.employee_id else employees.browse()

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
