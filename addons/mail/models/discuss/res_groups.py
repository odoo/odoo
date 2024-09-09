# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResGroups(models.Model):
    _inherit = "res.groups"

    def write(self, vals):
        res = super().write(vals)
        if vals.get("user_ids"):
            self.env["discuss.channel"].search([("group_ids", "in", self.all_implied_ids._ids)])._subscribe_users_automatically()
        return res
