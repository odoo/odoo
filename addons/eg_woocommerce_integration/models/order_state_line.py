from odoo import fields, models


class OrderStateLine(models.Model):
    _name = 'order.state.line'

    instance_id = fields.Many2one(comodel_name='eg.ecom.instance')

    woo_order_state = fields.Selection(
        [('pending', 'Pending'), ('processing', 'Processing'), ('on-hold', 'On Hold'), ('completed', 'Completed'),
         ('cancelled', 'Cancelled'), ('refunded', 'Refunded'), ('failed', 'Failed'), ('trash', 'Trash')],
        string="Woo Order State")

    odoo_order_state = fields.Selection(
        [('draft', 'Quotation'), ('sent', 'Quotation Sent'), ('sale', 'Sale Order'), ('done', 'Locked'),
         ('cancel', 'Cancel')], string="Odoo Order State")
