from odoo import fields, models


class SalePeppolAdvancedOrderTransaction(models.Model):
    _name = 'sale.peppol.advanced.order.transaction'
    _description = 'Model for tracking PEPPOL advanced order transactions'
    _order = 'sequence desc, id desc'

    sequence = fields.Integer()
    order_id = fields.Many2one(
        comodel_name='sale.order',
        required=True, ondelete='cascade', index=True, copy=False)
    order_change_ref = fields.Char('Order change document reference')
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
    company_id = fields.Many2one('res.company', related='order_id.company_id', string='Company', store=True, readonly=True)
