# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def write(self, vals):
        # Reschedule related pickings
        if self.env.user.has_group('sale_stock_renting.group_rental_stock_picking') and any(key in ['rental_start_date', 'rental_return_date'] for key in vals):
            confirmed_rental_orders = self.filtered(lambda so: so.is_rental_order and so.state == 'sale')
            for order in confirmed_rental_orders:
                if vals.get('rental_start_date') and order.rental_start_date:
                    delivery_moves_to_reschedule = order.order_line.move_ids.filtered(lambda m:
                        m.location_final_id == order.warehouse_id.company_id.rental_loc_id
                        and m.state not in ['done', 'cancel']
                    )
                    if delivery_moves_to_reschedule:
                        new_rental_start_date = fields.Datetime.to_datetime(vals['rental_start_date']) or order.rental_start_date
                        time_delta = new_rental_start_date - order.rental_start_date
                        for move in delivery_moves_to_reschedule:
                            move.date += time_delta
                            if move.date_deadline:
                                move.with_context(date_deadline_propagate_ids=set(move.move_dest_ids.ids)).date_deadline += time_delta
                if vals.get('rental_return_date') and order.rental_return_date:
                    return_moves_to_reschedule = order.order_line.move_ids.filtered(lambda m:
                        m.location_id == order.warehouse_id.company_id.rental_loc_id
                        and m.location_final_id == order.warehouse_id.lot_stock_id
                        and m.state not in ['done', 'cancel']
                    )
                    if return_moves_to_reschedule:
                        new_rental_return_date = fields.Datetime.to_datetime(vals['rental_return_date']) or order.rental_return_date
                        time_delta = new_rental_return_date - order.rental_return_date
                        for move in return_moves_to_reschedule:
                            move.date += time_delta
                            if move.date_deadline:
                                move.with_context(date_deadline_propagate_ids=set(move.move_orig_ids.ids)).date_deadline += time_delta
        return super().write(vals)

    def action_open_pickup(self):
        if any(s.is_rental for s in self.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')).move_ids.sale_line_id):
            ready_picking = self.picking_ids.filtered(lambda p: p.state == 'assigned' and p.picking_type_code == 'outgoing')
            if ready_picking:
                return self._get_action_view_picking(ready_picking)
            return self._get_action_view_picking(self.picking_ids)
        return super().action_open_pickup()

    def action_open_return(self):
        if any(s.is_rental for s in self.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')).move_ids.sale_line_id):
            ready_picking = self.picking_ids.filtered(lambda p: p.state == 'assigned' and p.picking_type_code == 'incoming')
            if ready_picking:
                return self._get_action_view_picking(ready_picking)
            return self._get_action_view_picking(self.picking_ids)
        return super().action_open_return()
