from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    l10n_sa_invoice_qr_code_str = fields.Char(related="account_move.l10n_sa_qr_code_str", string="ZATCA QR Code")
    l10n_sa_invoice_edi_state = fields.Selection(related="account_move.edi_state", string="Electronic invoicing")

    def is_settlement_order(self):
        self.ensure_one()
        """
        Check if the invoice is linked to a POS settlement order
        Only available when pos_settle_due module is installed
        """
        if not self.env["pos.order.line"]._fields.get("settled_order_id"):
            return False
        return bool(self.lines.filtered("settled_order_id"))
