from odoo import fields, models


class PurchasePeppolAdvancedOrderTracker(models.Model):
    _name = 'purchase.peppol.advanced.order.tracker'
    _description = 'Model for tracking PEPPOL advanced order transactions'
    _order = 'sequence desc, id desc'

    sequence = fields.Integer()
    order_id = fields.Many2one('purchase.order')
    attachment_id = fields.Many2one('ir.attachment', string="EDI Document", required=True)
    document_type = fields.Selection([
        ('order', 'Order'),
        ('order_change', 'Order Change'),
        ('order_cancel', 'Order Cancellation'),
    ], readonly=True)
    state = fields.Selection([
        ('sent', 'Sent'),
        ('to_reply', 'To Reply'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], string="Status")
