# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "bus.listener.mixin"]

    def _bus_channels(self):
        # sudo: res.partner - can find all active users linked to partner when sending a bus notification
        return self.sudo().with_context(active_test=True).user_ids._bus_channels()
