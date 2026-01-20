from odoo import fields, models


class PurchasePeppolAdvancedOrderTransaction(models.Model):
    _name = 'purchase.peppol.advanced.order.transaction'
    _description = 'Model for tracking PEPPOL advanced order transactions'
    _order = 'sequence desc, id desc'

    sequence = fields.Integer()
    order_id = fields.Many2one(
        comodel_name='purchase.order',
        required=True, ondelete='cascade', index=True, copy=False)
    order_change_ref = fields.Char('Order change document reference')
    attachment_id = fields.Many2one(
        'ir.attachment', string='EDI Document', required=True
    )
    document_type = fields.Selection(
        [
            ('order', 'Order'),
            ('order_change', 'Order Change'),
            ('order_cancel', 'Order Cancellation'),
            ('order_balance', 'Order Balance'),
        ],
        readonly=True,
    )
    state = fields.Selection(
        [
            ('sent', 'Sent'),
            ('to_reply', 'To Reply'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
    )
    company_id = fields.Many2one('res.company', related='order_id.company_id', string='Company', store=True, readonly=True)

    peppol_message_uuid = fields.Char(string='PEPPOL message ID')
    peppol_proxy_state = fields.Selection(
        selection=[
            ('skipped', 'Skipped (tests)'),
            ('processing', 'Processing'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
    )
