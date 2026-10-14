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
        self.env["bus.bus"]._subscribe_again(
            self.filtered(lambda user: user.all_group_ids != groups_before_by_user[user]),
        )
        return res
