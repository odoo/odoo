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
    manu_type_id = fields.Many2one(
        'stock.picking.type', 'Manufacturing Operation Type',
        domain=[('code', '=', 'mrp_operation')])
    manufacture_steps = fields.Selection([
                                ('manu_only', 'Produce'),
                                ('pick_manu', 'Pick the components + Produce')],
                                'Manufacture', default='manu_only', required=True,
                                help="Produce : Move the raw materials to the production location directly and start the manufacturing process.\nPick / Produce : Unload the raw materials from the Stock to Input location first, and then transfer it to the Production location.")
    wh_input_manu_loc_id = fields.Many2one("stock.location", "Manufacturing Input Location")
    manufacturing_pick_route_id = fields.Many2one('stock.location.route', 'Manufacture Pick Route', ondelete='restrict')

    def _create_or_update_manu_input_location(self):
        # This method is used to create/update locations of input type stock location.
        self.ensure_one()
        if not self.wh_input_manu_loc_id:
            self.wh_input_manu_loc_id = self.env['stock.location'].create({
                'name': _('PROD/IN'),
                'active': self.manufacture_steps != 'manu_only',
                'usage': 'internal',
                'location_id': self.view_location_id.id,
                'company_id': self.company_id.id}).id
        else:
            self.wh_input_manu_loc_id.active = self.manufacture_steps != 'manu_only'
        return True

    def _create_or_update_pull_rule(self, pull_vals, pull_rule=False):
        self.ensure_one()
        ProcurementRule = self.env['procurement.rule']
        if not pull_rule:
            pull_rule = ProcurementRule.with_context(active_test=False).search([
                        ('location_src_id', '=', pull_vals['location_src_id']),
                        ('location_id', '=', pull_vals['location_id']),
                        ('picking_type_id', '=', pull_vals['picking_type_id']),
                        ('warehouse_id', '=', pull_vals['warehouse_id']),
                        ('route_id', '=', pull_vals['route_id'])
                    ])
        if not pull_rule:
            pull_rule = ProcurementRule.create(pull_vals)
        else:
            pull_rule.write(pull_vals)
        return pull_rule

    def _create_or_update_manufacturing_picking_types(self):
        self.ensure_one()
        Sequence = self.env['ir.sequence']
        picking_type_obj = self.env['stock.picking.type']
        other_pick_type = picking_type_obj.search([('warehouse_id', '=', self.id)], order = 'sequence desc', limit=1)
        location_id, location_dest_id = (self.lot_stock_id.id if self.manufacture_steps == 'manu_only' else self.wh_input_manu_loc_id.id,
            self.lot_stock_id.id)
        vals = {'default_location_dest_id': location_dest_id,
                'default_location_src_id': location_id,
                'active': self.manufacture_to_resupply,
                'warehouse_id': self.id,
                'color': other_pick_type.color if other_pick_type else 0}
        # Create manufacturing picking type, if it does not exist else update its locations.
        if not self.manu_type_id:
            seq_id = Sequence.search([('code', '=', 'mrp.production')], limit=1)
            if not seq_id:
                seq_id = Sequence.sudo().create({'name': 'Production order', 'prefix': 'MO/', 'padding': 5})
            vals.update({'sequence_id': seq_id.id, 'name': 'Manufacture', 'code': 'mrp_operation'})
            self.manu_type_id = picking_type_obj.create(vals).id
        else:
            self.manu_type_id.write(vals)
        return True

    @api.multi
    def _get_manufacturing_route_values(self, route_name):
        return {
            'name': self._format_routename(route_type=route_name),
            'warehouse_selectable': True,
            'company_id': self.company_id.id,
            'product_selectable': False,
            'sequence': 10,
        }

    def _get_manufacture_route_id(self):
        # This method will create/update manufacture route.
        Route = self.env['stock.location.route']
        manufacture_route = self.env.ref('mrp.route_warehouse0_manufacture') or Route.with_context(active_test=False).search([('name', 'like', _('Manufacture'))], limit=1)
        if not manufacture_route:
            manufacture_route = Route.create(self._get_manufacturing_route_values('manu_only'))
        return manufacture_route.id

    def _create_or_update_manufacturing_mto_pull(self):
        # Create/update procurement rule and link it to the generic MTO route
        location_id = self.wh_input_manu_loc_id if self.manufacture_steps != 'manu_only' else self.env.ref('stock.location_production')
        routings = [self.Routing(self.lot_stock_id, location_id, self.int_type_id)]
        vals = self._get_mto_pull_rules_values(routings)[0]
        vals['propagate'] = False
        self._create_or_update_pull_rule(vals)
        return True

    def _get_route_name(self):
        names = super(StockWarehouse, self)._get_route_name()
        names.update({
                 'manu_only': _('Produce'),
                 'pick_manu': _('Pick/Produce')
               })
        return names

    def _create_or_update_manufacturing_pick_route(self):
        # Create or update route for material pick for manufacturing
        if self.manufacturing_pick_route_id:
            self.manufacturing_pick_route_id.write({'name':  self._format_routename(route_type=self.manufacture_steps)})
            self.manufacturing_pick_route_id.pull_ids.write({'active': False})
        else:
            self.manufacturing_pick_route_id = self.env['stock.location.route'].create(self._get_manufacturing_route_values(self.manufacture_steps)).id
        dummy, pull_rules_list1 = self._get_push_pull_rules_values(
            [self.Routing(self.lot_stock_id, self.wh_input_manu_loc_id, self.int_type_id)], values={'active': self.manufacture_steps != 'manu_only', 'route_id': self.manufacturing_pick_route_id.id},
            push_values=None, pull_values={'procure_method': 'make_to_stock', 'propagate': False})
        dummy, pull_rules_list2 = self._get_push_pull_rules_values(
            [self.Routing(self.wh_input_manu_loc_id, self.env.ref('stock.location_production'), self.int_type_id)], values={'active': self.manufacture_steps != 'manu_only', 'route_id': self.manufacturing_pick_route_id.id},
            push_values=None, pull_values={'procure_method': 'make_to_order', 'propagate': False})
        for pull_vals in pull_rules_list1 + pull_rules_list2:
            self._create_or_update_pull_rule(pull_vals)
        return self.manufacturing_pick_route_id.id

    def _create_or_update_manufacture_pull(self):
        # Create or update procurement rule and link it to the Manufacture route
        self.ensure_one()
        procurement_location = self.wh_input_manu_loc_id if self.manufacture_steps != 'manu_only' else self.lot_stock_id
        routings = [self.Routing(procurement_location, self.lot_stock_id, self.manu_type_id)]
        dummy, pull_vals = self._get_push_pull_rules_values(routings, pull_values={
                                'name': self._format_routename(_(' Manufacture')),
                                'action': 'manufacture',
                                'route_id': self._get_manufacture_route_id(),
                                'propagate': False,
                                'active': self.manufacture_to_resupply})
        manu_pull_id = self._create_or_update_pull_rule(pull_vals[0], self.manufacture_pull_id)
        return manu_pull_id.id

    def _create_or_update_manufacturing_routes(self):
        for warehouse in self:
            warehouse._create_or_update_manu_input_location()
            warehouse._create_or_update_manufacturing_picking_types()
            # This will update make to order pull rule for manufacturing.
            warehouse._create_or_update_manufacturing_mto_pull()
            # This will update pull rules of manufacture route.
            manu_pull = warehouse._create_or_update_manufacture_pull()
            # This will create manufacturing pick route to send raw material in production.
            manufacturing_pick_route_id = warehouse._create_or_update_manufacturing_pick_route()
            warehouse.write({'manufacture_pull_id': manu_pull,
                             'manufacturing_pick_route_id': manufacturing_pick_route_id,
                             'route_ids': [(4, manufacturing_pick_route_id)]})
        return True

    @api.multi
    def create_routes(self):
        self.ensure_one()
        res = super(StockWarehouse, self).create_routes()
        self._create_or_update_manufacturing_routes()
        return res

    @api.multi
    def write(self, vals):
        res = super(StockWarehouse, self).write(vals)
        if 'manufacture_to_resupply' in vals or vals.get('manufacture_steps'):
            self._create_or_update_manufacturing_routes()
        return res

    @api.multi
    def _get_all_routes(self):
        routes = super(StockWarehouse, self).get_all_routes_for_wh()
        routes |= self.filtered(lambda self: self.manufacture_to_resupply and self.manufacture_pull_id and self.manufacture_pull_id.route_id).mapped('manufacture_pull_id').mapped('route_id')
        return routes

    @api.multi
    def _update_name_and_code(self, name=False, code=False):
        res = super(StockWarehouse, self)._update_name_and_code(name, code)
        # change the manufacture procurement rule name
        for warehouse in self:
            if warehouse.manufacture_pull_id and name:
                warehouse.manufacture_pull_id.write({'name': warehouse.manufacture_pull_id.name.replace(warehouse.name, name, 1)})
        return res
