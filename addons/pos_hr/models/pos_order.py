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

    def _post_chatter_message(self, body):
        body += Markup("<br/>")
        body += _("Cashier %s", self.cashier)
        self.message_post(body=body)
