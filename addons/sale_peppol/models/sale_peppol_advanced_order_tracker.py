from odoo import fields, models


class SalePeppolAdvancedOrderTracker(models.Model):
    _name = 'sale.peppol.advanced.order.tracker'
    _description = 'Model for tracking PEPPOL advanced order transactions'
    _order = 'sequence desc, id desc'

    sequence = fields.Integer()
    order_id = fields.Many2one('sale.order')
    attachment_id = fields.Many2one('ir.attachment', string="EDI Document", required=True)
    document_type = fields.Selection([
        ('order', 'Order'),
        ('order_change', 'Order Change'),
        ('order_cancel', 'Order Cancellation'),
    ])
    state = fields.Selection([
        ('sent', 'Sent'),
        ('to_reply', 'To Reply'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], string="Status")
