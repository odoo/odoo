# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import bus, base

from odoo import models


class IrAttachment(models.Model, base.IrAttachment, bus.BusListenerMixin):

    def _bus_channel(self):
        return self.env.user._bus_channel()
