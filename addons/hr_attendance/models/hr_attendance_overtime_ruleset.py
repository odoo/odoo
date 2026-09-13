from odoo import fields, models


class HrAttendanceOvertimeRuleset(models.Model):
    _name = "hr.attendance.overtime.ruleset"
    _description = "Overtime Ruleset"

    name = fields.Char(required=True)
    description = fields.Html()
    rule_ids = fields.One2many(
        comodel_name="hr.attendance.overtime.rule",
        inverse_name="ruleset_id",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        default=lambda self: self.env.company.country_id,
    )
    rate_combination_mode = fields.Selection(
        selection=[
            ("max", "Maximum Rate"),
            ("sum", "Sum of all rates"),
        ],
        default="max",
        required=True,
        help="Controls how the rates from the different rules that apply are combined.\n"
        "  Max: use the highest rate. (e.g.: combined for 150% and 120 = 150%)\n"
        "  Sum: sum the *extra* pay (i.e. above 100%).\n"
        "    e.g.: combined rate for 150% & 120% = 100% (baseline) + (150-100)% + (120-100)% = 170%\n",
    )
    rules_count = fields.Count(count_of="rule_ids")
    active = fields.Boolean(
        default=True,
        readonly=False,
    )

    def _attendances_to_regenerate_for(self):
        self.check_singleton()
        eligible_versions = self.env["hr.version"].search(
            [("ruleset_id", "=", self.id)]
        )
        if not eligible_versions:
            return self.env["hr.attendance"]
        return self.env["hr.attendance"].search(
            [
                ("employee_id", "in", eligible_versions.employee_id.ids),
                ("date", ">=", min(eligible_versions.mapped("date_version"))),
            ]
        )

    def action_regenerate_overtimes(self):
        self._attendances_to_regenerate_for()._update_overtime()
