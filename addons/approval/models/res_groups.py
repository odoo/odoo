from odoo import models

from . import approval_trace as trace


class ResGroups(models.Model):
    _inherit = "res.groups"

    def write(self, vals):
        res = super().write(vals)
        if {"user_ids", "implied_ids", "all_user_ids"} & vals.keys():
            trace.ESCALATION.event("manager_cache_dropped", groups=self.ids)
        return res
