from collections import defaultdict
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.tools import convert


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
        compute="_compute_current_employee_skill_ids",
        search="_search_current_employee_skill_ids",
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

    def _individual_skill_command_field_names(self):
        return ("current_employee_skill_ids", "certification_ids", "employee_skill_ids")

    @api.depends(
        "employee_skill_ids.valid_to",
        "employee_skill_ids.skill_id",
        "employee_skill_ids.is_certification",
    )
    def _compute_current_employee_skill_ids(self):
        current_by_employee = (
            self.employee_skill_ids._current_individual_skills().grouped("employee_id")
        )
        for employee in self:
            employee.current_employee_skill_ids = current_by_employee.get(
                employee, self.env["hr.employee.skill"]
            )

    @api.depends(
        "employee_skill_ids.valid_to",
        "employee_skill_ids.skill_id",
        "employee_skill_ids.is_certification",
    )
    def _compute_skill_ids(self):
        for employee in self:
            employee.skill_ids = employee.current_employee_skill_ids.skill_id

    def _get_domain_for_current_employee_skills(self, skill_domain):
        skill_model = self.env["hr.employee.skill"]
        current = skill_model._search(
            Domain.AND(
                [skill_model._validity_domain(fields.Date.today()), skill_domain]
            )
        )
        return Domain("employee_skill_ids", "in", current)

    def _search_current_employee_skill_ids(self, operator, value):
        if operator not in ("in", "not in", "any"):
            raise NotImplementedError
        if operator == "any" and isinstance(value, Domain):
            skill_domain = value
        else:
            skill_domain = Domain("id", "in", value)
        result = self._get_domain_for_current_employee_skills(skill_domain)
        return ~result if operator == "not in" else result

    def _search_skill_ids(self, operator, value):
        if operator not in ("in", "not in"):
            raise NotImplementedError
        result = self._get_domain_for_current_employee_skills(
            Domain("skill_id", "in", value)
        )
        return ~result if operator == "not in" else result

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
        """Map each job to {(skill, level): summary} for what it requires today."""
        required = defaultdict(dict)
        jobs = self.env["hr.job"].search(
            [("current_job_skill_ids", "any", [("is_certification", "=", True)])]
        )
        for job in jobs:
            for cert in job.current_job_skill_ids.filtered("is_certification"):
                required[job][(cert.skill_id, cert.skill_level_id)] = (
                    f"{cert.skill_id.name}: {cert.skill_level_id.name}"
                )
        return required

    @api.model
    def _get_certification_expiry_by_employee(self, employees):
        """Map each employee to {(skill, level): valid_to} for the certifications held.

        ``valid_to`` is False for one that never expires, and the latest expiry
        among those already lapsed when none is still valid. Grouping by
        (employee, skill, level) rather than assigning per row matters because an
        employee may legitimately hold both a lapsed certification and its
        renewal, and last-write-wins picks whichever was iterated last.
        """
        today = fields.Date.today()
        held = self.env["hr.employee.skill"].search(
            Domain.AND(
                [
                    Domain("employee_id", "in", employees.ids),
                    Domain("is_certification", "=", True),
                ],
            ),
        )
        expiry = defaultdict(dict)
        grouped = held.grouped(
            lambda skill: (skill.employee_id, skill.skill_id, skill.skill_level_id)
        )
        for (employee, skill, level), certifications in grouped.items():
            current = certifications.filtered(
                lambda c: not c.valid_to or c.valid_to >= today
            )
            if current:
                without_expiry = current.filtered(lambda c: not c.valid_to)
                valid_to = False if without_expiry else max(current.mapped("valid_to"))
            else:
                valid_to = max(certifications.mapped("valid_to"))
            expiry[employee][(skill, level)] = valid_to
        return expiry

    @api.model
    def _add_certification_activity_to_employees(self):
        today = fields.Date.today()
        three_months_later = today + relativedelta(months=3)
        return_val = self.env["mail.activity"]

        job_skill_level_mapping = self._get_required_certifications_by_job()
        if not job_skill_level_mapping:
            return return_val

        employee_domain = Domain.AND(
            [
                Domain("job_id", "in", [job.id for job in job_skill_level_mapping]),
                Domain.OR(
                    [
                        Domain("user_id", "!=", False),
                        Domain("parent_id.user_id", "!=", False),
                        Domain("job_id.user_id", "!=", False),
                    ],
                ),
            ],
        )
        employees = self.env["hr.employee"].search(employee_domain)
        if not employees:
            return return_val

        employee_cert_data = self._get_certification_expiry_by_employee(employees)

        existing_activities = self.env["mail.activity"].search(
            Domain.AND(
                [
                    Domain("active", "=", True),
                    Domain("activity_category", "=", "upload_file"),
                    Domain("res_model", "=", "hr.employee"),
                    Domain("res_id", "in", employees.ids),
                ],
            ),
        )
        existing_activity_keys = {
            (act.res_id, act.summary) for act in existing_activities
        }

        # activity_schedule already creates one activity per record of the
        # recordset it is called on, in a single create(). Calling it per
        # employee paid the whole scheduling path -- activity type lookup, model
        # lookup, the mail create hooks -- once per activity instead of once per
        # group of employees that share a summary, a deadline and a responsible.
        to_schedule = defaultdict(lambda: self.env["hr.employee"])
        for employee in employees:
            job_id = employee.job_id
            responsible = (
                employee.user_id or employee.parent_id.user_id or job_id.user_id
            )
            if job_id not in job_skill_level_mapping or not responsible:
                continue

            for skill_level_key, summary in job_skill_level_mapping[job_id].items():
                if (employee.id, summary) in existing_activity_keys:
                    continue

                valid_to_date = employee_cert_data.get(employee, {}).get(
                    skill_level_key
                )
                if valid_to_date is not None and (
                    valid_to_date is False or valid_to_date > three_months_later
                ):
                    continue

                to_schedule[(summary, valid_to_date or today, responsible)] |= employee

        note = self.env._("Certification missing or expiring soon")
        for (summary, deadline, responsible), group in to_schedule.items():
            return_val += group.activity_schedule(
                act_type_xmlid="hr_skills.mail_activity_data_upload_certification",
                summary=summary,
                note=note,
                date_deadline=deadline,
                user_id=responsible.id,
            )

        return return_val

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
