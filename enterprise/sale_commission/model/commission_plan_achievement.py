# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class CommissionPlanAchievement(models.Model):
    _name = 'sale.commission.plan.achievement'
    _description = 'Commission Plan Achievement'
    _order = 'id'

    plan_id = fields.Many2one('sale.commission.plan', required=True, ondelete='cascade')

    type = fields.Selection([
        ('amount_invoiced', "Amount Invoiced"),
        ('amount_sold', "Amount Sold"),
        ('qty_invoiced', "Quantity Invoiced"),
        ('qty_sold', "Quantity Sold"),
    ], required=True)

    product_id = fields.Many2one('product.product', "Product")
    product_categ_id = fields.Many2one('product.category', "Category")

    rate = fields.Float("Rate", default=lambda self: 1 if self.plan_id.type == 'target' else 0.05, required=True)
