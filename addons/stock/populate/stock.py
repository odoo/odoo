# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import math
from datetime import datetime, timedelta
from itertools import product as cartesian_product
from collections import defaultdict

from odoo import models, api
from odoo.tools import populate, groupby

_logger = logging.getLogger(__name__)

# Take X first company to put some stock on it data (it is to focus data on these companies)
COMPANY_NB_WITH_STOCK = 3  # Need to be smaller than 5 (_populate_sizes['small'] of company)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _populate_factories(self):

        def get_tracking(values, counter, random):
            if values['type'] == 'product':
                return random.choices(['none', 'lot', 'serial'], [0.7, 0.2, 0.1])[0]
            else:
                return 'none'

        res = super()._populate_factories()
        res.append(('type', populate.iterate(['consu', 'service', 'product'], [0.3, 0.2, 0.5])))
        res.append(('tracking', populate.compute(get_tracking)))
        return res


class Warehouse(models.Model):
    _inherit = 'stock.warehouse'

    _populate_sizes = {'small': 6, 'medium': 12, 'large': 24}
    _populate_dependencies = ['res.company']

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models['res.company'][:COMPANY_NB_WITH_STOCK]

        def get_name(values, counter, random):
            return "WH-%d-%d" % (values['company_id'], counter)

        return [
            ('company_id', populate.iterate(company_ids)),
            ('name', populate.compute(get_name)),
            ('code', populate.constant("W{counter}")),
            ('reception_steps', populate.iterate(['one_step', 'two_steps', 'three_steps'], [0.6, 0.2, 0.2])),
            ('delivery_steps', populate.iterate(['ship_only', 'pick_ship', 'pick_pack_ship'], [0.6, 0.2, 0.2])),
        ]


class Location(models.Model):
    _inherit = 'stock.location'

    _populate_sizes = {'small': 50, 'medium': 2_000, 'large': 50_000}
    _populate_dependencies = ['stock.warehouse']

    def _populate(self, size):
        locations = super()._populate(size)

        random = populate.Random('stock_location_sample')
        locations_sample = self.browse(random.sample(locations.ids, len(locations.ids)))

        company_ids = self.env.registry.populated_models['res.company'][:COMPANY_NB_WITH_STOCK]
        warehouses = self.env['stock.warehouse'].browse(self.env.registry.populated_models['stock.warehouse'])

        warehouse_by_company = dict(groupby(warehouses, lambda ware: ware.company_id.id))
        loc_ids_by_company = dict(groupby(locations_sample, lambda loc: loc.company_id.id))

        scenario_index = 0
        for company_id in company_ids:
            loc_ids_by_company[company_id] = loc_ids_by_company[company_id][::-1]  # Inverse the order to use pop()
            warehouses = warehouse_by_company[company_id]

            nb_loc_by_warehouse = math.ceil(len(loc_ids_by_company[company_id]) / len(warehouses))

            for warehouse in warehouses:
                # Manage the ceil, the last warehouse can have less locations than others.
                nb_loc_to_take = min(nb_loc_by_warehouse, len(loc_ids_by_company[company_id]))
                if scenario_index % 3 == 0:
                    # Scenario 1 : remain companies with "normal" level depth keep 4 levels max
                    depth = 3  # Force the number of level to 3 (root doesn't count)
                elif scenario_index % 3 == 1:
                    # Scenario 2 : one company with very low level depth location tree (all child of root)
                    depth = 1
                else:
                    # Scenario 3 : one company with high depth location tree
                    depth = 20

                nb_by_level = int(math.log(nb_loc_to_take, depth)) + 1 if depth > 1 else nb_loc_to_take  # number of loc to put by level

                _logger.info("Create locations (%d) tree for one warehouse - depth : %d, width : %d" % (nb_loc_to_take, depth, nb_by_level))

                # Root is the lot_stock_id of warehouse
                root = warehouse.lot_stock_id

                def link_next_locations(parent, level):
                    if level < depth:
                        children = []
                        nonlocal nb_loc_to_take
                        nb_loc = min(nb_by_level, nb_loc_to_take)
                        nb_loc_to_take -= nb_loc
                        for i in range(nb_loc):
                            children.append(loc_ids_by_company[company_id].pop())

                        child_locations = self.env['stock.location'].concat(*children)
                        child_locations.location_id = parent
                        for child in child_locations:
                            link_next_locations(child, level + 1)

                link_next_locations(root, 0)
                scenario_index += 1

        # Change 20 % the usage of some no-leaf location into 'view' (instead of 'internal')
        to_views = locations_sample.filtered_domain([('child_ids', '!=', [])]).ids
        random = populate.Random('stock_location_views')
        self.browse(random.sample(to_views, int(len(to_views) * 0.2))).usage = 'view'

        return locations

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models['res.company'][:COMPANY_NB_WITH_STOCK]
        removal_strategies = self.env['product.removal'].search([])

        return [
            ('name', populate.constant("Loc-{counter}")),
            ('usage', populate.constant('internal')),
            ('removal_strategy_id', populate.randomize(removal_strategies.ids + [False])),
            ('company_id', populate.iterate(company_ids)),
        ]


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    _populate_sizes = {'small': 150, 'medium': 5_000, 'large': 60_000}
    _populate_dependencies = ['product.product', 'product.supplierinfo', 'stock.location']

    def _populate_factories(self):

        warehouse_ids = self.env.registry.populated_models['stock.warehouse']
        warehouses = self.env['stock.warehouse'].browse(warehouse_ids)

        location_by_warehouse = {
            warehouse.id: self.env['stock.location'].search([('id', 'child_of', warehouse.lot_stock_id.id)]).ids
            for warehouse in warehouses
        }

        all_product_ids = set(self.env.registry.populated_models['product.product'])

        supplierinfos = self.env['product.supplierinfo'].browse(self.env.registry.populated_models['product.supplierinfo'])

        # Valid product by company (a supplier info exist for this product+company_id)
        valid_product = defaultdict(set)
        for suplierinfo in supplierinfos:
            products = suplierinfo.product_id or suplierinfo.product_tmpl_id.product_variant_ids
            # Reordering rule is only on the storable product
            if products and products[0].type == 'product':
                valid_product[suplierinfo.company_id.id] |= set(products.ids)
        valid_product = {company_id: product_ids | valid_product[False] for company_id, product_ids in valid_product.items() if company_id}
        invalid_product = {company_id: list(all_product_ids - product_ids) for company_id, product_ids in valid_product.items() if company_id}
        valid_product = {company_id: list(product_ids) for company_id, product_ids in valid_product.items()}

        def get_company_id(values, counter, random):
            warehouse = self.env['stock.warehouse'].browse(values['warehouse_id'])
            return warehouse.company_id.id

        def get_location_product(iterator, field_name, model_name):
            random = populate.Random('get_location_product')

            # To avoid raise product_location_check : product/location/company (company is assure because warehouse doesn't share location for now)
            # Use generator to avoid cartisian product in memory
            generator_valid_product_loc_dict = {}
            generator_invalid_product_loc_dict = {}
            for warehouse in warehouses:
                # TODO: randomize cartesian product
                generator_valid_product_loc_dict[warehouse.company_id.id] = cartesian_product(
                    # Force to begin by the main location of the warehouse
                    [warehouse.lot_stock_id.id] + random.sample(location_by_warehouse[warehouse.id], len(location_by_warehouse[warehouse.id])),
                    random.sample(valid_product[warehouse.company_id.id], len(valid_product[warehouse.company_id.id]))
                )
                generator_invalid_product_loc_dict[warehouse.company_id.id] = cartesian_product(
                    [warehouse.lot_stock_id.id] + random.sample(location_by_warehouse[warehouse.id], len(location_by_warehouse[warehouse.id])),
                    random.sample(invalid_product[warehouse.company_id.id], len(invalid_product[warehouse.company_id.id]))
                )

            for values in iterator:
                # 95 % of the orderpoint will be valid (a supplier info exist for this product + company_id)
                if random.random() < 0.95:
                    loc_id, product_id = next(generator_valid_product_loc_dict[values['company_id']])
                else:
                    loc_id, product_id = next(generator_invalid_product_loc_dict[values['company_id']])

                values['product_id'] = product_id
                values['location_id'] = loc_id
                yield values

        return [
            ('active', populate.iterate([True, False], [0.95, 0.05])),
            ('warehouse_id', populate.iterate(warehouse_ids)),
            ('company_id', populate.compute(get_company_id)),
            ('_get_location_product', get_location_product),
            ('product_min_qty', populate.iterate([0.0, 2.0, 10.0], [0.6, 0.2, 0.2])),
            ('product_max_qty', populate.iterate([10.0, 20.0, 100.0], [0.6, 0.2, 0.2])),
            ('qty_multiple', populate.iterate([0.0, 1.0, 2.0, 10.0], [0.4, 0.2, 0.2, 0.2])),
        ]


class Inventory(models.Model):
    _inherit = 'stock.inventory'

    _populate_sizes = {'small': 5, 'medium': 10, 'large': 20}
    _populate_dependencies = ['stock.location']

    def _populate(self, size):
        inventories = super()._populate(size)

        def start_inventory_sample(sample_ratio):
            random = populate.Random('start_inventory_sample')
            inventories_to_start = self.browse(random.sample(inventories.ids, int(len(inventories.ids) * sample_ratio)))
            # Start empty to let the stock.inventory.line populate create lines
            inventories_to_start.start_empty = True
            for inventory in inventories_to_start:
                inventory.action_start()

        # Start 80 % of adjustment inventory
        start_inventory_sample(0.8)

        return inventories

    def _populate_factories(self):

        company_ids = self.env.registry.populated_models['res.company'][:COMPANY_NB_WITH_STOCK]
        valid_locations = self.env['stock.location'].search([
            ('company_id', 'in', company_ids),
            ('usage', 'in', ['internal', 'transit'])
        ])
        locations_by_company = dict(groupby(valid_locations, key=lambda loc: loc.company_id.id))
        locations_by_company = {company_id: self.env['stock.location'].concat(*locations) for company_id, locations in locations_by_company.items()}
        products = self.env['product.product'].browse(self.env.registry.populated_models['product.product']).filtered(lambda p: p.type == 'product')

        def get_locations_ids(values, counter, random):
            location_ids_company = locations_by_company[values['company_id']]
            # We set locations to ease the creation of stock.inventory.line
            # Should be larger enough to avoid the emptiness of generator_product_loc_dict
            return random.sample(location_ids_company.ids, int(len(location_ids_company.ids) * 0.5))

        def get_product_ids(values, counter, random):
            # We set products to ease the creation of stock.inventory.line
            # Should be larger enough to avoid the emptiness of generator_product_loc_dict
            return random.sample(products.ids, int(len(products.ids) * 0.5))

        return [
            ('name', populate.constant("Inventory-Pop-{counter}")),
            ('company_id', populate.iterate(company_ids)),
            ('location_ids', populate.compute(get_locations_ids)),
            ('product_ids', populate.compute(get_product_ids)),
        ]


class InventoryLine(models.Model):
    _inherit = 'stock.inventory.line'

    _populate_sizes = {'small': 500, 'medium': 5_000, 'large': 20_000}
    _populate_dependencies = ['stock.inventory']

    def _populate(self, size):
        inventory_lines = super()._populate(size)

        def create_missing_lots():
            _logger.info("Create lot/serial for inventory line to be ready to validate")
            lots_values = []
            for line in inventory_lines:
                if line.product_tracking == 'none':
                    continue
                lots_values.append({
                    'name': "InLine-%d" % line.id,
                    'product_id': line.product_id.id,
                    'company_id': line.inventory_id.company_id.id
                })
            lots = self.env['stock.production.lot'].create(lots_values).ids[::-1]
            for line in inventory_lines:
                if line.product_tracking == 'none':
                    continue
                line.prod_lot_id = lots.pop()

        def validate_inventory_sample(sample_ratio):
            # Validate the inventory adjustment, useful to have a stock at beginning
            inventories_ids = inventory_lines.inventory_id.ids
            random = populate.Random('validate_inventory')
            inventories_to_done = self.env['stock.inventory'].browse(random.sample(inventories_ids, int(len(inventories_ids) * sample_ratio)))
            _logger.info("Validate %d inventory adjustment" % len(inventories_to_done))
            for inventory in inventories_to_done:
                inventory.action_validate()

        # Create missing tracking lot/serial in batch
        create_missing_lots()

        # (Un)comment to test a DB with a current stock.
        # validate_inventory_sample(0.8)

        return inventory_lines

    def _populate_factories(self):

        inventories = self.env['stock.inventory'].browse(self.env.registry.populated_models['stock.inventory'])
        inventories = inventories.filtered(lambda i: i.state == 'confirm')

        def compute_product_location(iterator, field_name, model_name):
            random = populate.Random('compute_product_location')

            # To avoid create twice the same line inventory (avoid _check_no_duplicate_line) : product/location (limitation for lot)
            # Use generator to avoid cartisian product in memory
            generator_product_loc_dict = {}
            for inventory in inventories:
                # TODO: randomize cartesian product
                generator_product_loc_dict[inventory.id] = cartesian_product(
                    random.sample(inventory.location_ids, len(inventory.location_ids)),
                    random.sample(inventory.product_ids, len(inventory.product_ids))
                )

            for values in iterator:
                loc_id, product = next(generator_product_loc_dict[values['inventory_id']])
                values['product_id'] = product.id
                values['location_id'] = loc_id.id
                yield values

        def get_product_qty(values, counter, random):
            product = self.env['product.product'].browse(values['product_id'])
            if product.tracking == 'serial':
                return 1.0
            else:
                return random.randint(5, 25)

        return [
            ('inventory_id', populate.iterate(inventories.ids)),
            ('_compute_product_location', compute_product_location),
            ('product_qty', populate.compute(get_product_qty)),
        ]


class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    _populate_sizes = {'small': 10, 'medium': 30, 'large': 200}
    _populate_dependencies = ['stock.location']

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models['res.company'][:COMPANY_NB_WITH_STOCK]
        internal_locations = self.env['stock.location'].search([('company_id', 'in', company_ids), ('usage', '=', 'internal')])

        def get_name(values, counter, random):
            return "%d-%s-%d" % (values['company_id'], values['code'], counter)

        def _compute_default_locations(iterator, field_name, model_name):
            random = populate.Random('_compute_default_locations')
            locations_by_company = dict(groupby(internal_locations, key=lambda loc: loc.company_id.id))
            locations_by_company = {company_id: self.env['stock.location'].concat(*locations) for company_id, locations in locations_by_company.items()}

            for values in iterator:

                locations_company = locations_by_company[values['company_id']]
                # TODO : choice only location child of warehouse.lot_stock_id
                inter_location = random.choice(locations_company)
                values['warehouse_id'] = inter_location.get_warehouse().id
                if values['code'] == 'internal':
                    values['default_location_src_id'] = inter_location.id
                    values['default_location_dest_id'] = random.choice(locations_company - inter_location).id
                elif values['code'] == 'incoming':
                    values['default_location_dest_id'] = inter_location.id
                elif values['code'] == 'outgoing':
                    values['default_location_src_id'] = inter_location.id

                yield values

        def get_show_operations(values, counter, random):
            return values['code'] != 'incoming'  # Simulate onchange of form

        def get_show_reserved(values, counter, random):
            return values['show_operations'] and values['code'] != 'incoming'  # Simulate onchange of form

        return [
            ('company_id', populate.iterate(company_ids)),
            ('code', populate.iterate(['incoming', 'outgoing', 'internal'], [0.3, 0.3, 0.4])),
            ('name', populate.compute(get_name)),
            ('sequence_code', populate.constant("PT{counter}")),
            ('_compute_default_locations', _compute_default_locations),
            ('show_operations', populate.compute(get_show_operations)),
            ('show_reserved', populate.compute(get_show_reserved)),
        ]


class Picking(models.Model):
    _inherit = 'stock.picking'

    _populate_sizes = {'small': 100, 'medium': 2_000, 'large': 50_000}
    _populate_dependencies = ['stock.location', 'stock.picking.type', 'res.partner']

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models['res.company'][:COMPANY_NB_WITH_STOCK]

        picking_types_ids = self.env['stock.picking.type'].browse(self.env.registry.populated_models['stock.picking.type']).ids

        now = datetime.now()

        cross_company_locations = self.env['stock.location'].search([('company_id', '=', False)])
        locations_companies = self.env['stock.location'].search([('company_id', 'in', company_ids)])

        all_partners = self.env['res.partner'].browse(self.env.registry.populated_models['res.partner'])
        partners_by_company = dict(groupby(all_partners, key=lambda par: par.company_id.id))
        partners_inter_company = self.env['res.partner'].concat(*partners_by_company.get(False, []))
        partners_by_company = {com: self.env['res.partner'].concat(*partners) | partners_inter_company for com, partners in partners_by_company.items() if com}

        def get_until_date(values, counter, random):
            # 95.45 % of picking scheduled between (-10, 30) days and follow a gauss distribution (only +-15% picking is late)
            delta = random.gauss(10, 10)
            return now + timedelta(days=delta)

        def get_partner_id(values, counter, random):
            picking_type = self.env['stock.picking.type'].browse(values['picking_type_id'])
            company = picking_type.company_id
            return partners_by_company.get(company.id) and random.choice(partners_by_company[company.id]).id or False

        def _compute_locations(iterator, field_name, model_name):
            locations_out = cross_company_locations.filtered_domain([('usage', '=', 'customer')])
            locations_in = cross_company_locations.filtered_domain([('usage', '=', 'supplier')])
            locations_internal = locations_companies.filtered_domain([('usage', '=', 'internal')])
            locations_by_company = dict(groupby(locations_companies, key=lambda loc: loc.company_id.id))
            locations_by_company = {com: self.env['stock.location'].concat(*locs) for com, locs in locations_by_company.items()}

            random = populate.Random('_compute_locations')
            for values in iterator:
                picking_type = self.env['stock.picking.type'].browse(values['picking_type_id'])

                source_loc = picking_type.default_location_src_id
                dest_loc = picking_type.default_location_dest_id

                locations_company = locations_by_company[picking_type.company_id.id]
                if not source_loc or random.random() > 0.8:
                    if picking_type.code == 'incoming':
                        source_loc = random.choice(locations_in)
                    elif picking_type.code == 'outgoing':
                        source_loc = random.choice(locations_internal & locations_company)
                    elif picking_type.code == 'internal':
                        source_loc = random.choice(locations_internal & locations_company)

                if not dest_loc or random.random() > 0.8:
                    if picking_type.code == 'incoming':
                        dest_loc = random.choice(locations_internal & locations_company)
                    elif picking_type.code == 'outgoing':
                        dest_loc = random.choice(locations_out)
                    elif picking_type.code == 'internal':
                        # Need at most 2 internal locations
                        dest_loc = random.choice((locations_internal & locations_company) - source_loc)

                values['location_id'] = source_loc.id
                values['location_dest_id'] = dest_loc.id
                yield values

        return [
            ('priority', populate.randomize(['1', '0'], [0.05, 0.95])),
            ('scheduled_date', populate.compute(get_until_date)),
            ('picking_type_id', populate.iterate(picking_types_ids)),
            ('partner_id', populate.compute(get_partner_id)),
            ('_compute_locations', _compute_locations),
        ]


class StockMove(models.Model):
    _inherit = 'stock.move'

    _populate_sizes = {'small': 1_000, 'medium': 20_000, 'large': 1_000_000}
    _populate_dependencies = ['stock.picking']

    def _populate(self, size):
        moves = super()._populate(size)

        def confirm_pickings(sample_ratio):
            # Confirm sample_ratio * 100 % of picking
            random = populate.Random('confirm_pickings')
            picking_ids = moves.picking_id.ids
            picking_to_confirm = self.env['stock.picking'].browse(random.sample(picking_ids, int(len(picking_ids) * sample_ratio)))
            _logger.info("Confirm %d of pickings" % len(picking_to_confirm))
            picking_to_confirm.action_confirm()

        # (Un)comment to test a DB with a lot of outgoing/incoming/internal confirmed moves, e.g. for testing of forecasted report
        # confirm_pickings(0.8)

        return moves.exists()  # Confirm picking can unlink some moves

    @api.model
    def _populate_attach_record_weight(self):
        return ['picking_id'], [1]

    @api.model
    def _populate_attach_record_generator(self):
        picking_ids = self.env['stock.picking'].browse(self.env.registry.populated_models['stock.picking'])

        def next_picking_generator():
            while picking_ids:
                yield from picking_ids.ids

        return {'picking_id': next_picking_generator()}

    def _populate_factories(self):
        product_ids = self.env['product.product'].browse(self.env.registry.populated_models['product.product']).filtered(lambda p: p.type in ('product', 'consu'))

        def get_product_uom(values, counter, random):
            return self.env['product.product'].browse(values['product_id']).uom_id.id

        def _attach_to_record(iterator, field_name, model_name):
            random = populate.Random('_attach_to_record')
            fields, weights = self._populate_attach_record_weight()
            fields_generator = self._populate_attach_record_generator()

            for values in iterator:
                field = random.choices(fields, weights)[0]
                values[field] = next(fields_generator[field])
                yield values

        def _compute_picking_values(iterator, field_name, model_name):
            for values in iterator:
                if values.get('picking_id'):
                    picking = self.env['stock.picking'].browse(values['picking_id'])
                    values['picking_id'] = picking.id
                    values['location_id'] = picking.location_id.id
                    values['location_dest_id'] = picking.location_dest_id.id
                    values['name'] = picking.name
                    values['date'] = picking.scheduled_date
                    values['company_id'] = picking.company_id.id
                yield values

        return [
            ('product_id', populate.randomize(product_ids.ids)),
            ('product_uom', populate.compute(get_product_uom)),
            ('product_uom_qty', populate.randint(1, 10)),
            ('sequence', populate.randint(1, 1000)),
            ('_attach_to_record', _attach_to_record),
            ('_compute_picking_values', _compute_picking_values),
        ]
