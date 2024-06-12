# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    def _total_cost_per_hour(self):
        self.ensure_one()
        return self.workcenter_id.costs_hour
