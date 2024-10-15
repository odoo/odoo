# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import mrp


class MrpRoutingWorkcenter(mrp.MrpRoutingWorkcenter):

    def _total_cost_per_hour(self):
        self.ensure_one()
        return self.workcenter_id.costs_hour
