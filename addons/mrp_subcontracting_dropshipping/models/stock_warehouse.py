# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    subcontracting_dropshipping_to_resupply = fields.Boolean(
        'Dropship Subcontractors', default=True,
        help="Dropship subcontractors with components")

    subcontracting_dropshipping_pull_id = fields.Many2one(
        'stock.rule', 'Subcontracting-Dropshipping MTS Rule', copy=False
    )

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        # if new warehouse has resupply enabled, enable global route
        if any([vals.get('subcontracting_dropshipping_to_resupply', False) for vals in vals_list]):
            res.update_global_route_dropship_subcontractor()
        return res

    def write(self, vals):
        res = super().write(vals)
        # if all warehouses have resupply disabled, disable global route, until its enabled on a warehouse
        if 'subcontracting_dropshipping_to_resupply' in vals or 'active' in vals:
            if 'subcontracting_dropshipping_to_resupply' in vals:
                # ignore when warehouse archived since it will auto-archive all of its rules
                self._update_dropship_subcontract_rules()
            self.update_global_route_dropship_subcontractor()
        return res

    def _update_dropship_subcontract_rules(self):
        '''update (archive/unarchive) any warehouse subcontracting location dropship rules'''
        subcontracting_locations = self._get_subcontracting_locations()
        route_id = self._find_or_create_global_route('mrp_subcontracting_dropshipping.route_subcontracting_dropshipping',
                                           _('Dropship Subcontractor on Order'))
        warehouses_dropship = self.filtered(lambda w: w.subcontracting_dropshipping_to_resupply and w.active)
        if warehouses_dropship:
            self.env['stock.rule'].with_context(active_test=False).search([
                ('route_id', '=', route_id.id),
                ('action', '=', 'pull'),
                ('warehouse_id', 'in', warehouses_dropship.ids),
                ('location_src_id', 'in', subcontracting_locations.ids)]).action_unarchive()

        warehouses_no_dropship = self - warehouses_dropship
        if warehouses_no_dropship:
            self.env['stock.rule'].search([
                ('route_id', '=', route_id.id),
                ('action', '=', 'pull'),
                ('warehouse_id', 'in', warehouses_no_dropship.ids),
                ('location_src_id', 'in', subcontracting_locations.ids)]).action_archive()

    def update_global_route_dropship_subcontractor(self):
        route_id = self._find_or_create_global_route('mrp_subcontracting_dropshipping.route_subcontracting_dropshipping',
                                           _('Dropship Subcontractor on Order'))
        # if route has no pull rules, it means all warehouses have Dropship Subcontractor disabled
        # Pick type is per company so we need to check rules per company to archive it, however
        # the route is global so we need to check all rules regardless of company
        all_rules = route_id.sudo().rule_ids.filtered(lambda r: r.active)
        for company in self.company_id:
            company_rules = all_rules.filtered(lambda r: r.company_id == company)
            company.dropship_subcontractor_pick_type_id.active = bool(company_rules.filtered(lambda r: r.action == 'pull'))

        route_id.active = bool(all_rules.filtered(lambda r: r.action == 'pull'))

    def _generate_global_route_rules_values(self):
        rules = super()._generate_global_route_rules_values()
        subcontract_location_id = self._get_subcontracting_location()
        production_location_id = self._get_production_location()
        dropship_route = self.env.ref('stock_dropshipping.route_drop_shipping')
        rules.update({
            'subcontracting_dropshipping_pull_id': {
                'depends': ['subcontracting_dropshipping_to_resupply'],
                'create_values': {
                    'procure_method': 'make_to_order',
                    'company_id': self.company_id.id,
                    'action': 'pull',
                    'auto': 'manual',
                    'route_id': dropship_route.id,
                    'name': self._format_rulename(subcontract_location_id, production_location_id, False),
                    'location_dest_id': production_location_id.id,
                    'location_src_id': subcontract_location_id.id,
                    'picking_type_id': self.subcontracting_type_id.id
                },
                'update_values': {
                    'active': self.subcontracting_dropshipping_to_resupply
                }
            },
        })
        return rules
