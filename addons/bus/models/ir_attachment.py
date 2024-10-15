# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import base, bus


class IrAttachment(base.IrAttachment, bus.BusListenerMixin):

    def _bus_channel(self):
        return self.env.user._bus_channel()
