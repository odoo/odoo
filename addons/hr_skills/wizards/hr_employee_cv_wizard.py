from urllib.parse import urlencode

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrEmployeeCvWizard(models.TransientModel):
    _name = "hr.employee.cv.wizard"
    _description = "Print Resume"

    employee_ids = fields.Many2many(comodel_name="hr.employee")

    color_primary = fields.Char(
        string="Primary Color",
        default=lambda self: (
            self.env.company.report_config_id.primary_color or "#666666"
        ),
        required=True,
    )
    color_secondary = fields.Char(
        string="Secondary Color",
        default=lambda self: (
            self.env.company.report_config_id.secondary_color or "#666666"
        ),
        required=True,
    )

    show_skills = fields.Boolean(
        string="Skills",
        default=True,
    )
    show_contact = fields.Boolean(
        string="Contact Information",
        default=True,
    )
    show_others = fields.Boolean(
        string="Others",
        default=True,
    )

    can_show_others = fields.Boolean(compute="_compute_printable_sections")
    can_show_skills = fields.Boolean(compute="_compute_printable_sections")

    @api.depends("employee_ids")
    def _compute_printable_sections(self):
        language = self.env.ref(
            "hr_skills.hr_skill_type_lang", raise_if_not_found=False
        )
        for wizard in self:
            wizard.can_show_others = any(
                not line.line_type_id for line in wizard.employee_ids.resume_line_ids
            )
            wizard.can_show_skills = any(
                skill.skill_type_id != language
                for skill in wizard.employee_ids.employee_skill_ids._held_individual_skills()
            )

    def action_validate(self):
        self.check_singleton()
        printable = self.env["hr.employee"]._get_cv_printable_employees(
            self.employee_ids.ids
        )
        if not self.employee_ids or printable != self.employee_ids:
            _debug.logic(
                "cv_wizard_refused",
                requested=self.employee_ids,
                printable=printable,
                user=self.env.user,
            )
            raise UserError(
                self.env._("You can only print the resume of employees you can access.")
                if self.env.user.has_group("hr.group_hr_user")
                else self.env._("You can only print your own resume.")
            )
        query = {
            "employee_ids": ",".join(str(x) for x in self.employee_ids.ids),
            "color_primary": self.color_primary,
            "color_secondary": self.color_secondary,
        }
        for section in ("show_skills", "show_contact", "show_others"):
            if self[section]:
                query[section] = 1
        _debug.pipeline("cv_wizard_url", employees=self.employee_ids)
        return {
            "name": self.env._("Print Resume"),
            "type": "ir.actions.act_url",
            "url": "/print/cv?" + urlencode(query),
        }
