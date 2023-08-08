# Copyright 2022, Jarsa Sistemas, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class ReportPendingTransfers(models.Model):
    _inherit = "stock.picking"

    product_id = fields.Many2one(
        comodel_name="product.product",
    )

    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
    )

    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
    )
