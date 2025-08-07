from odoo import fields, models, api


class ARCAActivity(models.Model):
    _name = "l10n_ar.arca.activity"
    _description = "ARCA Activity"
    _order = "code"

    code = fields.Char(required=True, help="Activity Code")
    name = fields.Char(required=True, help="Activity Description")
    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("code", "name")
    def _compute_display_name(self):
        """Recompute the display name for the activity model so it is more user-friendly.
        Display name: Activity code + Activity description"""
        for activity in self:
            activity.display_name = "%s - %s" % (activity.code, activity.name)
