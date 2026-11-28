from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_cogs_value(self):
        self.ensure_one()
        if not self.product_id:
            return self.price_unit
        price_unit = super()._get_cogs_value()
        sudo_order = self.move_id.sudo().pos_order_ids
        if sudo_order:
            price_unit = sudo_order._get_pos_anglo_saxon_price_unit(self.product_id, self.quantity)
        return price_unit

    def _use_inventory_valuation(self):
        # The COGS of a session closing entry are added by the session (see
        # `_prepare_session_closing_extra_line_commands`), even if its lines have a product
        return super()._use_inventory_valuation() and not self.move_id.pos_session_ids

    def _compute_name(self):
        amls = self.filtered(lambda l: not l.move_id.pos_session_ids)
        super(AccountMoveLine, amls)._compute_name()
