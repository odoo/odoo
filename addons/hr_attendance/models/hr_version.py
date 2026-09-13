from odoo import api, fields, models


class HrVersion(models.Model):
    _name = "hr.version"
    _inherit = "hr.version"

    @api.model
    def _domain_current_countries(self):
        return [
            "|",
            ("country_id", "=", False),
            ("country_id", "in", self.env.companies.country_id.ids),
        ]

    ruleset_id = fields.Many2one(
        comodel_name="hr.attendance.overtime.ruleset",
        default=lambda self: self.env.ref(
            "hr_attendance.hr_attendance_default_ruleset", raise_if_not_found=False
        ),
        domain=_domain_current_countries,
        tracking=True,
        groups="hr.group_hr_manager",
    )
