# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ARCAActivity(models.Model):
    _name = "l10n_ar.arca.activity"
    _description = "ARCA Activity"
    _order = "code"
    _rec_names_search = ["name", "code"]

    code = fields.Char(required=True, help="Activity Code")
    name = fields.Char(required=True, help="Activity Description")

    _code_unique = models.Constraint(
        'UNIQUE(code)',
        "Activity code must be unique",
    )
    _code_length = models.Constraint(
        'CHECK(LENGTH(code) <= 6)',
        "Activity codes must be at most 6 characters long",
    )

    @api.depends("code", "name")
    @api.depends_context("formatted_display_name")
    def _compute_display_name(self):
        for activity in self:
            if activity.env.context.get("formatted_display_name"):
                activity.display_name = f"--{activity.code}--\t{activity.name}"
            else:
                activity.display_name = "%s - %s" % (activity.code, activity.name)
