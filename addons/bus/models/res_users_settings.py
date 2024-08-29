# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import bus, base

from odoo import models


class ResUsersSettings(models.Model, base.ResUsersSettings, bus.BusListenerMixin):

    def _bus_channel(self):
        return self.user_id._bus_channel()
