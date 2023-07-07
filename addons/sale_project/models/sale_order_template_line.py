# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class SaleOrderTemplateLine(models.Model):
    _inherit = 'sale.order.template.line'

    def _prepare_order_line_values(self):
        res = super()._prepare_order_line_values()
        # prevent the association of a related task on the SOL if a task would be generated when confirming the SO.
        if 'default_task_id' in self.env.context and \
                self.product_id.service_tracking in ['task_in_project', 'task_global_project']:
            res['task_id'] = False
        return res
