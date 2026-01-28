from odoo import api, models


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    @api.model
    def is_settlement_order(self, invoice):
        """
            Check if the invoice is linked to a POS settlement order
            Only available when pos_settle_due module is installed
        """
        if not self.env['pos.order.line']._fields.get('settled_order_id'):
            return False
        return any(line.settled_order_id for line in invoice.pos_order_ids.lines)

    def _get_move_applicability(self, move):
        # EXTENDS account_edi
        self.ensure_one()
        if self.code == 'sa_zatca' and move.country_code == 'SA' and move.move_type in ('out_invoice', 'out_refund') and self.is_settlement_order(move):
            return {}
        return super()._get_move_applicability(move)
