# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResGroups(models.Model):
    _name = 'res.groups'
    _inherit = ["res.groups", "bus.listener.mixin"]

    def write(self, vals):
        if not vals.keys() & {"implied_by_ids", "implied_ids", "user_ids"}:
            return super().write(vals)
        # sudo: res.groups - can read the users and implied groups of a group to notify its users
        before_by_group = {
            group: (group.all_user_ids, group.all_implied_ids) for group in self.sudo()
        }
        res = super().write(vals)
        users = self.env["res.users"]
        for group, (users_before, implied_before) in before_by_group.items():
            users_after = group.all_user_ids
            if implied_before != group.all_implied_ids:
                users |= users_before | users_after
            else:
                users |= (users_before | users_after) - (users_before & users_after)
        self.env["bus.bus"]._subscribe_again(users)
        return res
