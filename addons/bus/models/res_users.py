# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResUsers(models.Model):
    _name = "res.users"
    _inherit = ["res.users", "bus.listener.mixin"]

    def write(self, vals):
        if "group_ids" not in vals:
            return super().write(vals)
        groups_before_by_user = {user: user.all_group_ids for user in self}
        res = super().write(vals)
        for user in self:
            before, after = groups_before_by_user[user], user.all_group_ids
            self.env["bus.subscription.change"]._add_change(
                user,
                gained=after - before,
                lost=before - after,
            )
        return res
