# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    @api.model
    def update_rental_rules(self):
        warehouses = self.env['stock.warehouse'].sudo().search([])
        for warehouse in warehouses:
            warehouse._create_or_update_route()

    def get_rules_dict(self):
        """ Add or remove the push rules necessary for rental return pickings. """
        result = super().get_rules_dict()
        if self.env.user.has_group('sale_stock_renting.group_rental_stock_picking'):
            for warehouse in self:
                rental_location_id = warehouse.company_id.rental_loc_id
                if self.Routing(rental_location_id, warehouse.lot_stock_id, warehouse.in_type_id, 'push') not in result[warehouse.id].get('one_step'):
                    result[warehouse.id].update({
                        'one_step': result[warehouse.id]['one_step'] + [self.Routing(rental_location_id, warehouse.lot_stock_id, warehouse.in_type_id, 'push')],
                        'two_steps': result[warehouse.id]['two_steps'] + [self.Routing(rental_location_id, warehouse.wh_input_stock_loc_id, warehouse.in_type_id, 'push')],
                        'three_steps': result[warehouse.id]['three_steps'] + [self.Routing(rental_location_id, warehouse.wh_input_stock_loc_id, warehouse.in_type_id, 'push')],
                    })
        return result

    def _get_receive_rules_dict(self):
        """ Make sure that the push rules are always present for the rental location. """
        self.ensure_one()
        result = super()._get_receive_rules_dict()
        if self.env.user.has_group('sale_stock_renting.group_rental_stock_picking'):
            rental_location_id = self.company_id.rental_loc_id
            result.update({
                'one_step': result['one_step'] + [self.Routing(rental_location_id, self.lot_stock_id, self.in_type_id, 'push')],
                'two_steps': result['two_steps'] + [self.Routing(rental_location_id, self.wh_input_stock_loc_id, self.in_type_id, 'push')],
                'three_steps': result['three_steps'] + [self.Routing(rental_location_id, self.wh_input_stock_loc_id, self.in_type_id, 'push')],
            })
        return result
