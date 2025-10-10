from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    l10n_sa_invoice_qr_code_str = fields.Char(related="account_move.l10n_sa_qr_code_str", string="ZATCA QR Code")
    l10n_sa_invoice_edi_state = fields.Selection(related="account_move.edi_state", string="Electronic invoicing")
