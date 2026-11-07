from odoo import api, fields, models
from odoo.tools import format_date


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

    def _compute_name(self):
        amls = self.filtered(lambda l: not l.move_id.pos_session_ids)
        super(AccountMoveLine, amls)._compute_name()

    @api.depends('pos_order_line_id.pack_lot_ids.lot_name', 'pos_order_line_id.pack_lot_ids.expiration_date')
    def _compute_label(self):
        super()._compute_label()

        for line in self:
            lots = line.pos_order_line_id.pack_lot_ids.filtered('lot_name')
            if not lots:
                continue

            lot_details = []
            for lot in lots:
                if lot.expiration_date:
                    expiration_date = fields.Date.context_today(line, lot.expiration_date)
                    lot_details.append(f"{lot.lot_name} - {format_date(self.env, expiration_date)}")
                else:
                    lot_details.append(lot.lot_name)

            existing_lines = set((line.label or "").splitlines())
            lots_to_add = [detail for detail in dict.fromkeys(lot_details) if detail not in existing_lines]
            if lots_to_add:
                line.label = "\n".join(filter(None, [line.label, *lots_to_add]))
