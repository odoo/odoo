# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResGroups(models.Model):
    _name = 'res.groups'
    _inherit = ["res.groups", "bus.listener.mixin"]

    def write(self, vals):
        if not vals.keys() & {"implied_by_ids", "implied_ids", "user_ids"}:
            return super().write(vals)
        # sudo: res.groups - can read the users and implied groups of a group to follow their groups
        before_by_group = {
            group: (group.all_user_ids, group.all_implied_ids) for group in self.sudo()
        }
        res = super().write(vals)
        changes = self.env["bus.subscription.change"]
        for group, (users_before, implied_before) in before_by_group.items():
            users_after, implied_after = group.all_user_ids, group.all_implied_ids
            changes._add_change(users_after - users_before, gained=implied_after)
            kept_users = users_before & users_after
            changes._add_change(kept_users, gained=implied_after - implied_before)
            for implied in implied_before - implied_after:
                changes._add_change(kept_users - implied.all_user_ids, lost=implied)
            for user in users_before - users_after:
                changes._add_change(user, lost=implied_before - user.all_group_ids)
        return res
