# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, exceptions, fields, models, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    manufacture_to_resupply = fields.Boolean(
        'Manufacture in this Warehouse', default=True,
        help="When products are manufactured, they can be manufactured in this warehouse.")
    manufacture_pull_id = fields.Many2one(
        'procurement.rule', 'Manufacture Rule')

    @api.multi
    def write(self, vals):
        if 'manufacture_to_resupply' in vals:
            if vals.get("manufacture_to_resupply"):
                for warehouse in self.filtered(lambda warehouse: not warehouse.manufacture_pull_id):
                    manufacture_pull = warehouse._create_or_update_manufacture_pull(self.get_routes_dict())
                    vals['manufacture_pull_id'] = manufacture_pull.id
            else:
                self.mapped('manufacture_pull_id').unlink()
        return super(StockWarehouse, self).write(vals)

    @api.multi
    def get_routes_dict(self):
        result = super(StockWarehouse, self).get_routes_dict()
        for warehouse in self:
            result[warehouse.id]['manufacture'] = [self.Routing(warehouse.lot_stock_id, warehouse.lot_stock_id, warehouse.int_type_id)]
        return result

    def _get_manufacture_route_id(self):
        manufacture_route_id = self.env.ref('mrp.route_warehouse0_manufacture').id
        if not manufacture_route_id:
            manufacture_route_id = self.env['stock.location.route'].search([('name', 'like', _('Manufacture'))], limit=1).id
        if not manufacture_route_id:
            raise exceptions.UserError(_('Can\'t find any generic Manufacture route.'))
        return manufacture_route_id

    def _get_manufacture_pull_rules_values(self, route_values):
        dummy, pull_rules_list = self._get_push_pull_rules_values(route_values, pull_values={
            'name': self._format_routename(_(' Manufacture')),
            'location_src_id': False,  # TDE FIXME
            'action': 'manufacture',
            'route_id': self._get_manufacture_route_id(),
            'propagate': False,
            'active': True})
        return pull_rules_list

    def _create_or_update_manufacture_pull(self, routes_data):
        routes_data = routes_data or self.get_routes_dict()
        for warehouse in self:
            routings = routes_data[warehouse.id]['manufacture']
            if warehouse.manufacture_pull_id:
                manufacture_pull = warehouse.manufacture_pull_id
                manufacture_pull.write(warehouse._get_manufacture_pull_rules_values(routings)[0])
            else:
                manufacture_pull = self.env['procurement.rule'].create(warehouse._get_manufacture_pull_rules_values(routings)[0])
        return manufacture_pull

    @api.multi
    def create_routes(self):
        res = super(StockWarehouse, self).create_routes()
        self.ensure_one()
        routes_data = self.get_routes_dict()
        manufacture_pull = self._create_or_update_manufacture_pull(routes_data)
        res['manufacture_pull_id'] = manufacture_pull.id
        return res

    @api.multi
    def _get_all_routes(self):
        routes = super(StockWarehouse, self).get_all_routes_for_wh()
        routes |= self.filtered(lambda self: self.manufacture_to_resupply and self.manufacture_pull_id and self.manufacture_pull_id.route_id).mapped('manufacture_pull_id').mapped('route_id')
        return routes

    @api.multi
    def _handle_renaming(self, name, code):
        res = super(StockWarehouse, self)._handle_renaming(name, code)
        # change the manufacture procurement rule name
        for warehouse in self:
            if warehouse.manufacture_pull_id:
                warehouse.manufacture_pull_id.write({'name': warehouse.manufacture_pull_id.name.replace(warehouse.name, name, 1)})
        return res
