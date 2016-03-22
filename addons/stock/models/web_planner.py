# -*- coding: utf-8 -*-

from odoo import models


class PlannerInventory(models.Model):
    _inherit = 'web.planner'

    def _get_planner_application(self):
        planner = super(PlannerInventory, self)._get_planner_application()
        planner.append(['planner_inventory', 'Inventory Planner'])
        return planner
