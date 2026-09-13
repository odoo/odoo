from odoo import fields, models
from odoo.models import ValuesType


class ResUsers(models.Model):
    _inherit = "res.users"

    resource_ids = fields.One2many(
        comodel_name="resource.resource",
        inverse_name="user_id",
        string="Resources",
    )
    resource_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        related="resource_ids.calendar_id",
        string="Default Working Hours",
        readonly=False,
    )

    def write(self, vals: ValuesType) -> bool:
        rslt = super().write(vals)

        if (
            vals.get("tz")
            and len(self) == 1
            and not self.env.user.login_date
            and self.env.user == self.env.ref("base.user_admin", False)
            and self == self.env.user
        ):
            if self.resource_calendar_id:
                self.resource_calendar_id.tz = vals["tz"]
            elif default_calendar := self.env.ref(
                "resource.resource_calendar_std", False
            ):
                default_calendar.tz = vals["tz"]

        return rslt
