# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.osv import expression


class Task(models.Model):
    _inherit = "project.task"

    def action_fsm_view_material(self):
        res = super().action_fsm_view_material()
        res['domain'] = expression.AND([res['domain'], [('recurring_invoice', '=', False)]])
        return res
