from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _reconcile_account_move_lines(self, data):
        data = super()._reconcile_account_move_lines(data)
        pay_later_move_lines = data.get('pay_later_move_lines')
        # Reconcile customer receivable move lines
        if pay_later_move_lines:
            account_ids = pay_later_move_lines.mapped("account_id")
            partner_ids = pay_later_move_lines.mapped("partner_id")
            pay_later_move_lines |= pay_later_move_lines.search(
                [
                    "|",
                    ("journal_id", "=", self.config_id.journal_id.id),
                    "&",
                    ("move_type", "=", "out_invoice"),
                    ("move_id.pos_order_ids", "!=", False),
                    ("account_id", "in", account_ids.ids),
                    ("partner_id", "in", partner_ids.ids),
                    ("reconciled", "=", False),
                    ("parent_state", "=", "posted"),
                ]
            )
            for partner in pay_later_move_lines.mapped("partner_id"):
                pay_later_move_lines.filtered(lambda p: p.partner_id.id == partner.id).reconcile()
        return data
