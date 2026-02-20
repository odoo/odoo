# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrAttachment(models.Model):
    _name = 'ir.attachment'
    _inherit = ["ir.attachment", "bus.listener.mixin"]

    def _bus_channels(self):
        return self.env.user._bus_channels()
