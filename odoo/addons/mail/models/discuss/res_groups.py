# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResGroups(models.Model):
    _inherit = "res.groups"

    def write(self, vals):
        res = super().write(vals)
        if vals.get("users"):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_ids = [command[1] for command in vals["users"] if command[0] == 4]
            user_ids += [id for command in vals["users"] if command[0] == 6 for id in command[2]]
            self.env["discuss.channel"].search([("group_ids", "in", self._ids)])._subscribe_users_automatically()
        return res
