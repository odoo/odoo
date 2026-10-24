# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResUsers(models.Model):
    _name = "res.users"
    _inherit = ["res.users", "bus.listener.mixin"]

    def write(self, vals):
        res = super().write(vals)
        if "group_ids" in vals:
            self.env["bus.bus"]._subscribe_again(self)
        return res
