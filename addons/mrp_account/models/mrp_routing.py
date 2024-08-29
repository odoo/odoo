# -*- coding: utf-8 -*-
from odoo.addons import mrp
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MrpRoutingWorkcenter(models.Model, mrp.MrpRoutingWorkcenter):

    def _total_cost_per_hour(self):
        self.ensure_one()
        return self.workcenter_id.costs_hour
