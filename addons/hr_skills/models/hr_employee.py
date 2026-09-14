from collections import defaultdict
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import convert

_debug = DebugLog(__name__)


class HrEmployee(models.Model):
    _inherit = ["mixin.hr.individual.skill.owner", "hr.employee"]

    resume_line_ids = fields.One2many(
        comodel_name="hr.resume.line",
        inverse_name="employee_id",
        string="Resume lines",
    )
    employee_skill_ids = fields.One2many(
        comodel_name="hr.employee.skill",
        inverse_name="employee_id",
        string="Skills",
        domain=[("skill_type_id.active", "=", True)],
    )
    current_employee_skill_ids = fields.One2many(
        comodel_name="hr.employee.skill",
        compute="_compute_current_individual_skill_ids",
        search="_search_current_individual_skill_ids",
        readonly=False,
    )
    skill_ids = fields.Many2many(
        comodel_name="hr.skill",
        compute="_compute_skill_ids",
        search="_search_skill_ids",
        groups="hr.group_hr_user",
    )
    certification_ids = fields.One2many(
        comodel_name="hr.employee.skill",
        compute="_compute_certification_ids",
        readonly=False,
    )
    display_certification_page = fields.Boolean(
        compute="_compute_display_certification_page"
    )

    def _individual_skill_field_name(self):
        return "employee_skill_ids"

    def _current_individual_skill_field_name(self):
        return "current_employee_skill_ids"

    def _individual_skill_command_field_names(self):
        return (*super()._individual_skill_command_field_names(), "certification_ids")

    @api.depends("employee_skill_ids.is_certification")
    def _compute_certification_ids(self):
        for employee in self:
            employee.certification_ids = employee.employee_skill_ids.filtered(
                "is_certification"
            )

    def _compute_display_certification_page(self):
        self.display_certification_page = bool(
            self.env["hr.skill.type"]._get_certification_type()
        )

    @api.model
    def _get_required_certifications_by_job(self):
        job_skill_model = self.env["hr.job.skill"]
        return job_skill_model.search(
            job_skill_model._domain_held(fields.Date.today())
            & Domain("is_certification", "=", True)
            & Domain("skill_type_id.active", "=", True)
            & Domain("job_id.active", "=", True)
        ).grouped("job_id")

    @staticmethod
    def _certification_covered_until(certifications, today):
        covered_until = today - relativedelta(days=1)
        for certification in certifications.sorted("valid_from"):
            if certification.valid_from > covered_until + relativedelta(days=1):
                break
            if not certification.valid_to:
                return False
            covered_until = max(covered_until, certification.valid_to)
        return covered_until if covered_until >= today else None

    @api.model
    def _add_certification_activity_to_employees(self):
        today = fields.Date.today()
        three_months_later = today + relativedelta(months=3)
        activities = self.env["mail.activity"]

        requirements_by_job = self._get_required_certifications_by_job()
        if not requirements_by_job:
            _debug.logic("certification_cron", by="no_requirements")
            return activities

        employees = self.env["hr.employee"].search(
            Domain("job_id", "in", [job.id for job in requirements_by_job])
            & (
                Domain("user_id", "!=", False)
                | Domain("parent_id.user_id", "!=", False)
                | Domain("job_id.user_id", "!=", False)
            )
        )
        if not employees:
            _debug.logic("certification_cron", by="no_employees_in_jobs")
            return activities

        certifications = (
            self.env["hr.employee.skill"]
            .search(
                Domain("employee_id", "in", employees.ids)
                & Domain("is_certification", "=", True)
            )
            .grouped(lambda row: (row.employee_id, row.skill_id))
        )
        activity_type = self.env.ref(
            "hr_skills.mail_activity_data_upload_certification"
        )
        existing_activity_keys = {
            (
                activity.res_id,
                activity.certification_skill_id,
                activity.certification_skill_level_id,
            )
            for activity in self.env["mail.activity"].search(
                Domain("activity_type_id", "=", activity_type.id)
                & Domain("res_model", "=", "hr.employee")
                & Domain("res_id", "in", employees.ids)
            )
        }

        # activity_schedule already creates one activity per record of the
        # recordset it is called on, in a single create(). Calling it per
        # employee paid the whole scheduling path -- activity type lookup, model
        # lookup, the mail create hooks -- once per activity instead of once per
        # group of employees that share a summary, a deadline and a responsible.
        to_schedule = defaultdict(lambda: self.env["hr.employee"])
        for employee in employees:
            responsible = (
                employee.user_id
                or employee.parent_id.user_id
                or employee.job_id.user_id
            )
            if not responsible:
                continue
            for requirement in requirements_by_job.get(employee.job_id, ()):
                if (
                    employee.id,
                    requirement.skill_id,
                    requirement.skill_level_id,
                ) in existing_activity_keys:
                    continue
                qualifying = certifications.get(
                    (employee, requirement.skill_id), self.env["hr.employee.skill"]
                ).filtered(
                    lambda row, requirement=requirement: (
                        row.level_progress >= requirement.level_progress
                    )
                )
                covered_until = self._certification_covered_until(qualifying, today)
                if covered_until is False or (
                    covered_until and covered_until > three_months_later
                ):
                    continue
                deadline = covered_until or max(
                    (
                        row.valid_to
                        for row in qualifying
                        if row.valid_to and row.valid_to < today
                    ),
                    default=today,
                )
                to_schedule[
                    (
                        requirement.skill_id,
                        requirement.skill_level_id,
                        deadline,
                        responsible,
                    )
                ] |= employee

        note = self.env._("Certification missing or expiring soon")
        _debug.pipeline(
            "certification_cron",
            employees=employees,
            jobs=len(requirements_by_job),
            existing=len(existing_activity_keys),
            groups=len(to_schedule),
        )
        for (skill, level, deadline, responsible), group in to_schedule.items():
            activities += group.activity_schedule(
                act_type_xmlid="hr_skills.mail_activity_data_upload_certification",
                summary=f"{skill.name}: {level.name}",
                note=note,
                date_deadline=deadline,
                user_id=responsible.id,
                certification_skill_id=skill.id,
                certification_skill_level_id=level.id,
            )
        _debug.lifecycle("certification_activities", activities=activities)
        return activities

    @api.model
    def _get_cv_printable_employees(self, employee_ids):
        """The employees the current user may print, or an empty recordset.

        An HR user prints whichever employees they can read; anyone else prints
        only themself. The report renders as superuser, so this is the only
        access check it gets.
        """
        user = self.env.user
        employees = self.browse(employee_ids).exists()
        if not user._is_internal() or len(employees) != len(set(employee_ids)):
            _debug.logic("cv_print_denied", by="not_internal_or_missing", user=user)
            return self.browse()
        if user.has_group("hr.group_hr_user"):
            _debug.logic("cv_print", by="hr_user", user=user, employees=employees)
            return employees if employees.has_access("read") else self.browse()
        _debug.logic("cv_print", by="self_only", user=user, employees=employees)
        return employees if employees == user.employee_id else self.browse()

    def _load_scenario(self):
        super()._load_scenario()
        demo_tag = self.env.ref(
            "hr_skills.employee_resume_line_emp_eg_1", raise_if_not_found=False
        )
        if demo_tag:
            return
        convert.convert_file(
            self.env,
            "hr_skills",
            "data/scenarios/hr_skills_scenario.xml",
            None,
            mode="init",
        )

    @api.model
    def get_internal_resume_lines(self, res_id, res_model):
        if not res_id:
            return []
        if res_model == "res.users":
            res_id = self.env["res.users"].browse(res_id).employee_id.id
        if not self.env["hr.employee"].browse(res_id).has_access("read"):
            raise AccessError(
                self.env._("You cannot access the resume of this employee.")
            )
        versions = self.env["hr.employee"].sudo().browse(res_id).version_ids
        return self._internal_resume_lines(
            versions,
            clip_to_contract=self.env["hr.version"]._has_field_access(
                self.env["hr.version"]._fields["contract_date_end"], "read"
            ),
        )

    @api.model
    def _version_span(self, version, next_version, clip_to_contract):
        """The days ``version`` describes: from its start to the day before the
        next version, narrowed to the contract when the reader may see one."""
        start = version.date_version
        end = (
            next_version.date_version - relativedelta(days=1) if next_version else False
        )
        if clip_to_contract:
            if version.contract_date_start:
                start = max(start, version.contract_date_start)
            if version.contract_date_end:
                end = min(end or date.max, version.contract_date_end)
        return start, end

    @api.model
    def _internal_resume_lines(self, versions, clip_to_contract=True):
        """One line per run of consecutive versions sharing a job title, most
        recent first. A version without a title is a hole between runs; a run
        ends where the contract does, even if the next version carries on."""
        lines = []
        for version, next_version in zip(versions, [*versions[1:], None], strict=True):
            if not version.job_title:
                continue
            start, end = self._version_span(version, next_version, clip_to_contract)
            previous = lines[-1] if lines else None
            if (
                previous
                and previous["job_title"] == version.job_title
                and previous["date_end"]
                and previous["date_end"] + relativedelta(days=1) == version.date_version
            ):
                previous.update(id=version.id, date_end=end)
                continue
            lines.append(
                {
                    "id": version.id,
                    "job_title": version.job_title,
                    "date_start": start,
                    "date_end": end,
                }
            )
        return lines[::-1]
