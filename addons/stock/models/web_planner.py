# -*- coding: utf-8 -*-
from openerp import models


class PlannerInventory(models.Model):

    _inherit = 'web.planner'

    def _get_planner_application(self):
        planner = super(PlannerInventory, self)._get_planner_application()
        planner.append(['planner_inventory', 'Inventory Planner'])
        return planner

    def _prepare_planner_inventory_data(self):
        return {
            'uom_menu_id': self.env.ref('stock.menu_stock_uom_form_action').id
        }
