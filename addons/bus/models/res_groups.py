# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import bus, base

from odoo import models


class ResGroups(models.Model, base.ResGroups, bus.BusListenerMixin):
