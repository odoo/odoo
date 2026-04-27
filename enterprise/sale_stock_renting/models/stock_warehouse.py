# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    @api.model
    def update_rental_rules(self):
        warehouses = self.env['stock.warehouse'].sudo().search([])
        for warehouse in warehouses:
            warehouse._create_or_update_route()

    def _create_or_update_route(self):
        warehouse_rental_route = self.env.ref('sale_stock_renting.route_rental')
        if not self.env.user.has_group('sale_stock_renting.group_rental_stock_picking'):
            if warehouse_rental_route.active:
                warehouse_rental_route.rule_ids.active = False
                warehouse_rental_route.active = False
            return super()._create_or_update_route()
        warehouse_rental_route.active = True
        rental_rules = self.env['stock.rule'].with_context(active_test=False).search([
            ('route_id', '=', warehouse_rental_route.id),
            ('warehouse_id', 'in', self.ids)
        ])
        rule_by_warehouse = {rule.warehouse_id.id: rule for rule in rental_rules}
        for warehouse in self:
            rule = rule_by_warehouse.get(warehouse.id)
            source_location = warehouse.company_id.rental_loc_id
            destination_location = warehouse.lot_stock_id
            if rule:
                rule.active = True
                continue
            self.env['stock.rule'].create({
                'name': warehouse._format_rulename(source_location, destination_location, f'rental-{warehouse.code}-'),
                'route_id': warehouse_rental_route.id,
                'location_src_id': source_location.id,
                'location_dest_id': destination_location.id,
                'action': 'pull',
                'auto': 'manual',
                'picking_type_id': warehouse.in_type_id.id,
                'procure_method': 'make_to_stock',
                'warehouse_id': warehouse.id,
                'company_id': warehouse.company_id.id,
            })
        return super()._create_or_update_route()
