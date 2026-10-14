# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResGroups(models.Model):
    _name = 'res.groups'
    _inherit = ["res.groups", "bus.listener.mixin"]

    def write(self, vals):
        if not vals.keys() & {"implied_by_ids", "implied_ids", "user_ids"}:
            return super().write(vals)
        # sudo: res.users - can read the users of a group to notify them that it changed
        users_before_by_group = {group: group.all_user_ids for group in self.sudo()}
        res = super().write(vals)
        users = self.env["res.users"]
        for group, users_before in users_before_by_group.items():
            users_after = group.all_user_ids
            changed_users = users_before | users_after
            if "implied_ids" not in vals:
                changed_users -= users_before & users_after
            users |= changed_users
        self.env["bus.bus"]._subscribe_again(users)
        return res
