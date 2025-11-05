from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    peppol_message_uuid = fields.Char(string='PEPPOL message ID')
    peppol_order_state = fields.Selection(
        selection=[
            ('ready', 'Ready to send'),
            ('to_send', 'Queued'),
            ('skipped', 'Skipped'),
            ('processing', 'Pending Reception'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        store=True,
        string='PEPPOL status',
        copy=False,
    )
