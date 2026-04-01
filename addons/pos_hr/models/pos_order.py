# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from markupsafe import Markup


class PosOrder(models.Model):
    _inherit = "pos.order"

    employee_id = fields.Many2one('hr.employee', string="Cashier", help="The employee who uses the cash register.")
    cashier = fields.Char(string="Cashier name", compute="_compute_cashier", store=True)

    @api.depends('employee_id', 'user_id')
    def _compute_cashier(self):
        for order in self:
            if order.employee_id:
                order.cashier = order.employee_id.name
            else:
                order.cashier = order.user_id.name

    def _prepare_pos_log(self, body):
        return super()._prepare_pos_log(body) + Markup("<br/>") + _("Cashier %s", self.cashier)
