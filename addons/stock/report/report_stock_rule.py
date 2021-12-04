# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class ReportStockRule(models.AbstractModel):
    _name = 'report.stock.report_stock_rule'
    _description = 'Stock rule report'

    @api.model
    def _get_report_values(self, docids, data=None):
        # Overriding data values here since used also in _get_routes.
        data['product_id'] = data.get('product_id', docids)
        data['warehouse_ids'] = data.get('warehouse_ids', [])

        product = self.env['product.product'].browse(data['product_id'])
        warehouses = self.env['stock.warehouse'].browse(data['warehouse_ids'])

        routes = self._get_routes(data)

        # Some routes don't have a warehouse_id but contain rules of different warehouses,
        # we filter here the ones we want to display and build for each one a dict containing the rule,
        # their source and destination location.
        relevant_rules = routes.mapped('rule_ids').filtered(lambda r: not r.warehouse_id or r.warehouse_id in warehouses)
        rules_and_loc = []
        for rule in relevant_rules:
            rules_and_loc.append(self._get_rule_loc(rule, product))

        locations = self._sort_locations(rules_and_loc, warehouses)
        reordering_rules = self.env['stock.warehouse.orderpoint'].search([('product_id', '=', product.id)])
        locations |= reordering_rules.mapped('location_id').filtered(lambda l: l not in locations)
        locations_names = locations.mapped('display_name')
        # Here we handle reordering rules and putaway strategies by creating the header_lines dict. This dict is indexed
        # by location_id and contains itself another dict with the relevant reordering rules and putaway strategies.
        header_lines = {}
        for location in locations:
            # TODO: group the RR by location_id to avoid a filtered at each loop
            rr = reordering_rules.filtered(lambda r: r.location_id.id == location.id)
            putaways = product.putaway_rule_ids.filtered(lambda p: p.location_in_id.id == location.id)
            if putaways or rr:
                header_lines[location.id] = {'putaway': [], 'orderpoint': []}
                for putaway in putaways:
                    header_lines[location.id]['putaway'].append(putaway)
                for r in rr:
                    header_lines[location.id]['orderpoint'].append(r)
        route_lines = []
        colors = self._get_route_colors()
        for color_index, route in enumerate(routes):
            rules_to_display = route.rule_ids & relevant_rules
            if rules_to_display:
                route_color = colors[color_index % len(colors)]
                color_index = color_index + 1
                for rule in rules_to_display:
                    rule_loc = [r for r in rules_and_loc if r['rule'] == rule][0]
                    res = []
                    for x in range(len(locations_names)):
                        res.append([])
                    idx = locations_names.index(rule_loc['destination'].display_name)
                    tpl = (rule, 'destination', route_color, )
                    res[idx] = tpl
                    idx = locations_names.index(rule_loc['source'].display_name)
                    tpl = (rule, 'origin', route_color, )
                    res[idx] = tpl
                    route_lines.append(res)
        return {
            'docs': product,
            'locations': locations,
            'header_lines': header_lines,
            'route_lines': route_lines,
        }

    @api.model
    def _get_route_colors(self):
        return ['#FFA500', '#800080', '#228B22', '#008B8B', '#4682B4', '#FF0000', '#32CD32']

    @api.model
    def _get_routes(self, data):
        """ Extract the routes to display from the wizard's content.
        """
        product = self.env['product.product'].browse(data['product_id'])
        warehouse_ids = self.env['stock.warehouse'].browse(data['warehouse_ids'])
        return product.route_ids | product.categ_id.total_route_ids | warehouse_ids.mapped('route_ids')

    @api.model
    def _get_rule_loc(self, rule, product):
        rule.ensure_one()
        return {'rule': rule, 'source': rule.location_src_id, 'destination': rule.location_id}

    @api.model
    def _sort_locations(self, rules_and_loc, warehouses):
        """ We order the locations by setting first the locations of type supplier and manufacture,
            then we add the locations grouped by warehouse and we finish by the locations of type
            customer and the ones that were not added by the sort.
        """
        all_src = self.env['stock.location'].concat(*([r['source'] for r in rules_and_loc]))
        all_dest = self.env['stock.location'].concat(*([r['destination'] for r in rules_and_loc]))
        all_locations = all_src | all_dest
        ordered_locations = self.env['stock.location']
        locations = all_locations.filtered(lambda l: l.usage in ('supplier', 'production'))
        for warehouse_id in warehouses:
            all_warehouse_locations = all_locations.filtered(lambda l: l.get_warehouse() == warehouse_id)
            starting_rules = [d for d in rules_and_loc if d['source'] not in all_warehouse_locations]
            if starting_rules:
                start_locations = self.env['stock.location'].concat(*([r['destination'] for r in starting_rules]))
            else:
                starting_rules = [d for d in rules_and_loc if d['source'] not in all_dest]
                start_locations = self.env['stock.location'].concat(*([r['source'] for r in starting_rules]))
            used_rules = self.env['stock.rule']
            locations |= self._sort_locations_by_warehouse(rules_and_loc, used_rules, start_locations, ordered_locations, warehouse_id)
            if any(location not in locations for location in all_warehouse_locations):
                remaining_locations = self.env['stock.location'].concat(*([r['source'] for r in rules_and_loc])).filtered(lambda l: l not in locations)
                locations |= self._sort_locations_by_warehouse(rules_and_loc, used_rules, remaining_locations, ordered_locations, warehouse_id)
        locations |= all_locations.filtered(lambda l: l.usage in ('customer'))
        locations |= all_locations.filtered(lambda l: l not in locations)
        return locations

    @api.model
    def _sort_locations_by_warehouse(self, rules_and_loc, used_rules, start_locations, ordered_locations, warehouse_id):
        """ We order locations by putting first the locations that are not the destination of others and do it recursively.
        """
        start_locations = start_locations.filtered(lambda l: l.get_warehouse() == warehouse_id)
        ordered_locations |= start_locations
        rules_start = []
        for rule in rules_and_loc:
            if rule['source'] in start_locations:
                rules_start.append(rule)
                used_rules |= rule['rule']
        if rules_start:
            rules_start_dest_locations = self.env['stock.location'].concat(*([r['destination'] for r in rules_start]))
            remaining_rules = self.env['stock.rule'].concat(*([r['rule'] for r in rules_and_loc])) - used_rules
            remaining_rules_location = self.env['stock.location']
            for r in rules_and_loc:
                if r['rule'] in remaining_rules:
                    remaining_rules_location |= r['destination']
            start_locations = rules_start_dest_locations - ordered_locations - remaining_rules_location
            ordered_locations = self._sort_locations_by_warehouse(rules_and_loc, used_rules, start_locations, ordered_locations, warehouse_id)
        return ordered_locations
