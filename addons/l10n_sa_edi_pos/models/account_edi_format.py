from odoo import api, models


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    @api.model
    def _move_has_settle_or_deposit_pos_order(self, invoice):
        """
            Check if the invoice is linked to a POS settlement order
            Only available when pos_settle_due module is installed
        """
        if not hasattr(self.env['pos.order.line'], '_is_settle_or_deposit'):
            return False
        return any(line._is_settle_or_deposit() for line in invoice.sudo().pos_order_ids.lines)

    def _get_move_applicability(self, move):
        # EXTENDS account_edi
        self.ensure_one()
        if self.code == 'sa_zatca' and move.country_code == 'SA' and move.move_type in ('out_invoice', 'out_refund') and self._move_has_settle_or_deposit_pos_order(move):
            return {}
        return super()._get_move_applicability(move)
