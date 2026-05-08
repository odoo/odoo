from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_invoiced_lot_values(self):
        self.ensure_one()

        lot_values = super()._get_invoiced_lot_values()

        if self.state == 'draft':
            return lot_values

        # user may not have access to POS orders, but it's ok if they have
        # access to the invoice
        for order in self.sudo().pos_order_ids:
            for line in order.lines:
                for lot in line.pack_lot_ids:
                    stock_lot = self._get_stock_lot_from_pos_lot(lot)
                    lot_values.append({
                        'product_name': lot.product_id.name,
                        'quantity': line.qty if lot.product_id.tracking == 'lot' else 1.0,
                        'uom_name': line.product_uom_id.name,
                        'lot_name': lot.lot_name,
                        'pos_lot_id': lot.id,
                        'lot_id': stock_lot.id,
                    } | (self._extract_extra_invoiced_lot_values(stock_lot) if stock_lot else {}))

        return lot_values

    def _get_stock_lot_from_pos_lot(self, pos_lot):
        """Return the stock lot matching a POS lot name.

        POS order lines store lot/serial numbers in ``pos.pack.operation.lot``.
        Extra invoice lot values, however, are computed from ``stock.lot``.
        """
        self.ensure_one()
        pos_lot.ensure_one()

        if not pos_lot.lot_name:
            return self.env['stock.lot']
        company = pos_lot.order_id.company_id or self.company_id
        return self.env['stock.lot'].sudo().search([
            '|', ('company_id', '=', False), ('company_id', '=', company.id),
            ('product_id', '=', pos_lot.product_id.id),
            ('name', '=', pos_lot.lot_name),
        ], limit=1)
