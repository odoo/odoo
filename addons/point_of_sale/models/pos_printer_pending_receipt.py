# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class PosPrinterPendingReceipt(models.TransientModel):
    _name = 'pos.printer.pending.receipt'
    _description = 'Point of Sale Printer Pending Receipt'
    _transient_max_count = 30  # 30 receipts maximum for all PoS configs (will be vacuumed every 5 minutes)
    _transient_max_hours = 0.1  # Each receipt will be kept for 6 minutes maximum (will be vacuumed every 5 minutes)

    receipt = fields.Text(string="Receipt")
    pos_config_id = fields.Char(string="POS Config ID")
