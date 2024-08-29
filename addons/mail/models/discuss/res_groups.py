# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import base

from odoo import models


class ResGroups(models.Model, base.ResGroups):

    def write(self, vals):
        res = super().write(vals)
        if vals.get("users"):
            self.env["discuss.channel"].search([("group_ids", "in", self._ids)])._subscribe_users_automatically()
        return res
