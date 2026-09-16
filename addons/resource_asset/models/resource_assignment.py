from odoo import api, fields, models

from .resource_asset import CUSTODY_ROLE_BY_FIELD


class ResourceAssignment(models.Model):
    _inherit = "resource.assignment"

    @api.model_create_multi
    def create(self, vals_list):
        assignments = super().create(vals_list)
        if self.env.context.get("custody_sync"):
            return assignments
        now = fields.Datetime.now()
        started = assignments.filtered(
            lambda assignment: (
                assignment.custody_role in CUSTODY_ROLE_BY_FIELD.values()
                and assignment.date_start <= now
                and (not assignment.date_end or assignment.date_end > now)
            )
        )
        if not started:
            return assignments
        # One live holder per role: whoever takes an asset over supersedes the
        # holder it had, however the row was created.
        asset_model = self.env["resource.asset"]
        rivals = (
            asset_model._search_live_custody(started.resource_id) - assignments
        ).filtered(
            lambda rival: any(
                rival.resource_id == assignment.resource_id
                and rival.custody_role == assignment.custody_role
                for assignment in started
            )
        )
        asset_model._end_custody(rivals, now)
        return assignments
