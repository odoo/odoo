from odoo import models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, bom):
        res = super()._prepare_mo_vals(product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, bom)
        if values.get('sale_line_id'):
            res['sale_line_id'] = values['sale_line_id']
        return res

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values):
        move_values = super()._get_stock_move_values(product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values)
        if (sol_id := values.get('sale_line_id')) is not None and 'product_id' in move_values:
            # if the SOL is for a kit
            sol = self.env['sale.order.line'].browse(sol_id)
            if move_values['product_id'] != sol.product_id.id:
                active_moves = sol.move_ids.filtered(lambda m: m.state != 'cancel')
                bom_line_id = active_moves.bom_line_id.filtered(
                    lambda bl: bl.product_id.id == move_values.get('product_id')
                )[:1].id
                if bom_line_id:
                    move_values['bom_line_id'] = bom_line_id
        return move_values

    def _notify_responsible_no_bom(self, procurement):
        super()._notify_responsible_no_bom(procurement)
        origin_orders = procurement.values.get('reference_ids').sale_ids if procurement.values.get('reference_ids') else False
        if origin_orders:
            notified_users = procurement.product_id.responsible_id.partner_id | origin_orders.user_id.partner_id
            self._post_no_bom_notification(origin_orders, notified_users, procurement.product_id)
