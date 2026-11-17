# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    sale_order_id = fields.Many2one(
        string="Sales Order",
        comodel_name="sale.order",
        readonly=True,
        copy=False,
        index="btree_not_null",
    )
