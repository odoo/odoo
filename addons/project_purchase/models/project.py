# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Project(models.Model):
    _inherit = "project.project"

    purchase_order_count = fields.Integer(related="analytic_account_id.purchase_order_count")

    def action_view_purchase_orders(self):
        self.ensure_one()
        return self.analytic_account_id.action_view_purchase_orders()
