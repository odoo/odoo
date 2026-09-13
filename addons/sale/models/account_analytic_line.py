from odoo import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    so_line = fields.Many2one(
        comodel_name="sale.order.line",
        string="Sales Order Item",
        index="btree_not_null",
        domain=[("qty_transferred_method", "=", "analytic")],
    )
