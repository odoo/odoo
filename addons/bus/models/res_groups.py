# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import base, bus


class ResGroups(base.ResGroups, bus.BusListenerMixin):
