from odoo import api, models


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

        if 'pos_order_line_id' not in self.env['account.move.line']._fields:
            return

        for line in self:
            pos_line = line.pos_order_line_id

            if pos_line and pos_line.pack_lot_ids:
                lot_details = []

                for lot in pos_line.pack_lot_ids.filtered('lot_name'):
                    if hasattr(lot, 'expiration_date') and lot.expiration_date:
                        lot_details.append(f"{lot.lot_name} - {lot.expiration_date}")
                    else:
                        lot_details.append(lot.lot_name)

                unique_lot_details = list(dict.fromkeys(lot_details))
                if unique_lot_details:
                    current_label = line.label or ""
                    line.label = current_label + "\n" + "\n".join(unique_lot_details)
