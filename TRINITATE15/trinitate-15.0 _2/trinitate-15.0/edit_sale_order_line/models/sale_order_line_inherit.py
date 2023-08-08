from odoo import models, fields


class SaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'

    can_modify = fields.Boolean(related='product_id.can_modify',string='Can Modify',store=True,)
