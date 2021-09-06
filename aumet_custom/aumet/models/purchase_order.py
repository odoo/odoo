import logging

from odoo import models, fields
_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    state = fields.Selection([
        ('draft', 'RFQ'),
        ('in marketplace', 'In Marketplace'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False,  tracking=True)

    def button_marketplace(self):
        pass

