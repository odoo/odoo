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


class Warehouse(models.Model):
    _inherit = 'stock.warehouse'

    _populate_sizes = {'small': 6, 'medium': 12, 'large': 24}
    _populate_dependencies = ['res.company']

    def _populate(self, size):
        # Activate options used in the stock populate to have a ready Database

        _logger.info("Activate settings for stock populate")
        self.env['res.config.settings'].create({
            'group_stock_production_lot': True,  # Activate lot
            'group_stock_tracking_lot': True,  # Activate package
            'group_stock_multi_locations': True,  # Activate multi-locations
            'group_stock_tracking_owner': True,  # Activate owner_id
        }).execute()

        return super()._populate(size)

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


class StorageCategory(models.Model):
    _inherit = 'stock.storage.category'

    _populate_sizes = {'small': 10, 'medium': 20, 'large': 50}

    def _populate(self, size):
        # Activate options used in the stock populate to have a ready Database

        self.env['res.config.settings'].create({
            'group_stock_storage_categories': True,  # Activate storage categories
        }).execute()

        return super()._populate(size)

    def _populate_factories(self):

        return [
            ('name', populate.constant("SC-{counter}")),
            ('max_weight', populate.iterate([10, 100, 500, 1000])),
            ('allow_new_product', populate.randomize(['empty', 'same', 'mixed'], [0.1, 0.1, 0.8])),
        ]


class Location(models.Model):
    _inherit = 'stock.location'

    _populate_sizes = {'small': 50, 'medium': 2_000, 'large': 50_000}
    _populate_dependencies = ['stock.warehouse', 'stock.storage.category']

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
                    depth = 10

                nb_by_level = int(math.log(nb_loc_to_take, depth)) + 1 if depth > 1 else nb_loc_to_take  # number of loc to put by level

                _logger.info("Create locations (%d) tree for a warehouse (%s) - depth : %d, width : %d" % (nb_loc_to_take, warehouse.code, depth, nb_by_level))

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
                        child_locations.location_id = parent  # Quite slow, because the ORM flush each time
                        for child in child_locations:
                            link_next_locations(child, level + 1)

                link_next_locations(root, 0)
                scenario_index += 1

        # Change 20 % the usage of some no-leaf location into 'view' (instead of 'internal')
        to_views = locations_sample.filtered_domain([('child_ids', '!=', [])]).ids
        random = populate.Random('stock_location_views')
        view_locations = self.browse(random.sample(to_views, int(len(to_views) * 0.1)))
        view_locations.write({
            'usage': 'view',
            'storage_category_id': False,
        })

        return locations

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models['res.company'][:COMPANY_NB_WITH_STOCK]
        removal_strategies = self.env['product.removal'].search([])
        storage_category_ids = self.env.registry.populated_models['stock.storage.category']

        def get_storage_category_id(values, counter, random):
            if random.random() > 0.5:
                return random.choice(storage_category_ids)
            return False

        return [
            ('name', populate.constant("Loc-{counter}")),
            ('usage', populate.constant('internal')),
            ('removal_strategy_id', populate.randomize(removal_strategies.ids + [False])),
            ('company_id', populate.iterate(company_ids)),
            ('storage_category_id', populate.compute(get_storage_category_id)),
        ]


class StockPutawayRule(models.Model):
    _inherit = 'stock.putaway.rule'

    _populate_sizes = {'small': 10, 'medium': 20, 'large': 50}
    _populate_dependencies = ['stock.location', 'product.product']

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models['res.company'][:COMPANY_NB_WITH_STOCK]
        product_ids = self.env['product.product'].browse(self.env.registry.populated_models['product.product']).filtered(lambda p: p.type == 'product').ids
        product_categ_ids = self.env.registry.populated_models['product.category']
        storage_categ_ids = self.env.registry.populated_models['stock.storage.category']
        location_ids = self.env['stock.location'].browse(self.env.registry.populated_models['stock.location']).filtered(lambda loc: loc.usage == 'internal')

        def get_product_id(values, counter, random):
            if random.random() > 0.5:
                return random.choice(product_ids)
            return False

        def get_category_id(values, counter, random):
            if not values['product_id']:
                return random.choice(product_categ_ids)
            return False

        def get_location_in_id(values, counter, random):
            locations = location_ids.filtered(lambda loc: loc.company_id.id == values['company_id'])
            return random.choice(locations.ids)

        def get_location_out_id(values, counter, random):
            child_locs = self.env['stock.location'].search([
                ('id', 'child_of', values['location_in_id']),
                ('usage', '=', 'internal')
            ]) + self.env['stock.location'].browse(values['location_in_id'])
            return random.choice(child_locs.ids)

        return [
            ('company_id', populate.randomize(company_ids)),
            ('product_id', populate.compute(get_product_id)),
            ('category_id', populate.compute(get_category_id)),
            ('location_in_id', populate.compute(get_location_in_id)),
            ('location_out_id', populate.compute(get_location_out_id)),
            ('sequence', populate.randint(1, 1000)),
            ('storage_category_id', populate.randomize(storage_categ_ids)),
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

            # To avoid raise product_location_check : product/location/company (company is ensure because warehouse doesn't share location for now)
            # Use generator to avoid cartisian product in memory
            generator_valid_product_loc_dict = {}
            generator_invalid_product_loc_dict = {}
            for warehouse in warehouses:
                # TODO: randomize cartesian product
                generator_valid_product_loc_dict[warehouse.id] = cartesian_product(
                    # Force to begin by the main location of the warehouse
                    [warehouse.lot_stock_id.id] + random.sample(location_by_warehouse[warehouse.id], len(location_by_warehouse[warehouse.id])),
                    random.sample(valid_product[warehouse.company_id.id], len(valid_product[warehouse.company_id.id]))
                )
                generator_invalid_product_loc_dict[warehouse.id] = cartesian_product(
                    [warehouse.lot_stock_id.id] + random.sample(location_by_warehouse[warehouse.id], len(location_by_warehouse[warehouse.id])),
                    random.sample(invalid_product[warehouse.company_id.id], len(invalid_product[warehouse.company_id.id]))
                )

            for values in iterator:
                # 95 % of the orderpoint will be valid (a supplier info exist for this product + company_id)
                if random.random() < 0.95:
                    loc_id, product_id = next(generator_valid_product_loc_dict[values['warehouse_id']])
                else:
                    loc_id, product_id = next(generator_invalid_product_loc_dict[values['warehouse_id']])

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


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    _populate_sizes = {'small': 100, 'medium': 5000, 'large': 20000}
    _populate_dependencies = ['stock.location', 'product.product']

    def _populate_factories(self):

        product_ids = self.env['product.product'].search([
            ('id', 'in', self.env.registry.populated_models['product.product']),
            ('type', '=', 'product'),
            ('tracking', '=', 'none')
        ]).ids
        locations = self.env['stock.location'].search([
            ('id', 'in', self.env.registry.populated_models['stock.location']),
            ('usage', '=', 'internal'),
        ])

        return [
            ('location_id', populate.randomize(locations.ids)),
            ('product_id', populate.randomize(product_ids)),
            ('inventory_quantity', populate.randint(0, 100)),
        ]

    def _populate(self, size):
        res = super(StockQuant, self.with_context(inventory_move=True))._populate(size)

        _logger.info("Apply %d inventories line", len(res))
        res.action_apply_inventory()

        return res

class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    _populate_sizes = {'small': 9, 'medium': 30, 'large': 200}
    _populate_dependencies = ['stock.location']

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models['res.company'][:COMPANY_NB_WITH_STOCK]
        warehouses = self.env['stock.warehouse'].browse(self.env.registry.populated_models['stock.warehouse'])
        internal_locations = self.env['stock.location'].search([('company_id', 'in', company_ids), ('usage', '=', 'internal')])
        in_warehouse_locations = self.env['stock.location'].search([('id', 'child_of', warehouses.lot_stock_id.ids)])
        internal_locations &= in_warehouse_locations

        def get_name(values, counter, random):
            return "%d-%s-%d" % (values['company_id'], values['code'], counter)

        def _compute_default_locations(iterator, field_name, model_name):
            random = populate.Random('_compute_default_locations')
            locations_by_company = dict(groupby(internal_locations, key=lambda loc: loc.company_id.id))
            locations_by_company = {company_id: self.env['stock.location'].concat(*locations) for company_id, locations in locations_by_company.items()}

            for values in iterator:

                locations_company = locations_by_company[values['company_id']]
                inter_location = random.choice(locations_company)
                values['warehouse_id'] = inter_location.warehouse_id.id
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

        def get_owner_id(values, counter, random):
            picking_type = self.env['stock.picking.type'].browse(values['picking_type_id'])
            company = picking_type.company_id
            if company.id not in partners_by_company:
                return False
            if random.random() < 0.10:  # For 10 % of picking, force owner_id
                random.choice(partners_by_company[company.id]).id

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
            ('owner_id', populate.compute(get_owner_id)),
            ('_compute_locations', _compute_locations),
        ]


class StockMove(models.Model):
    _inherit = 'stock.move'

    _populate_sizes = {'small': 1_000, 'medium': 20_000, 'large': 1_000_000}
    _populate_dependencies = ['stock.picking', 'product.product']

    def _populate(self, size):
        moves = super()._populate(size)

        def confirm_pickings(sample_ratio):
            # Confirm sample_ratio * 100 % of picking
            random = populate.Random('confirm_pickings')
            picking_ids = moves.picking_id.ids
            picking_to_confirm = self.env['stock.picking'].browse(random.sample(picking_ids, int(len(picking_ids) * sample_ratio)))
            _logger.info("Confirm %d pickings" % len(picking_to_confirm))
            picking_to_confirm.action_confirm()
            return picking_to_confirm

        def assign_picking(pickings):
            _logger.info("Assign %d pickings" % len(pickings))
            pickings.action_assign()

        def validate_pickings(pickings, sample_ratio):
            # Fill picking and validate it
            random = populate.Random('validate_pickings')
            picking_ids = pickings.ids
            picking_to_validate = self.env['stock.picking'].browse(random.sample(picking_ids, int(len(picking_ids) * sample_ratio)))

            _logger.info("Fill %d pickings with sml" % len(picking_to_validate))
            sml_values = []
            lot_values = []
            package_values = []
            for picking in picking_to_validate:
                package_for_picking = None
                if random.random() < 0.20:  # 20 % of chance to use package
                    package_for_picking = {'name': picking.name}
                for move in picking.move_lines:
                    # For assigned moves
                    for move_line in move._get_move_lines():
                        move_line.qty_done = move_line.product_uom_qty
                    # Create move line for remaining qty
                    missing_to_do = move.product_qty - move.quantity_done
                    missing_to_do = move.product_uom._compute_quantity(missing_to_do, move.product_uom, rounding_method='HALF-UP')
                    if move.product_id.tracking == 'serial':
                        for i in range(int(missing_to_do)):
                            lot_values.append({
                                'name': "ValPick-%d-%d--%d" % (move.id, move.product_id.id, i),
                                'product_id': move.product_id.id,
                                'company_id': move.company_id.id
                            })
                            sml_values.append(dict(
                                **move._prepare_move_line_vals(),
                                qty_done=1,
                                lot_id=len(lot_values) - 1,
                                package_id=package_for_picking and len(package_values) - 1 or False
                            ))
                    elif move.product_id.tracking == 'lot':
                        lot_values.append({
                            'name': "ValPick-%d-%d" % (move.id, move.product_id.id),
                            'product_id': move.product_id.id,
                            'company_id': move.company_id.id
                        })
                        sml_values.append(dict(
                            **move._prepare_move_line_vals(),
                            qty_done=missing_to_do,
                            lot_id=len(lot_values) - 1,
                            package_id=package_for_picking and len(package_values) - 1 or False
                        ))
                    else:
                        sml_values.append(dict(
                            **move._prepare_move_line_vals(),
                            qty_done=missing_to_do,
                            package_id=package_for_picking and len(package_values) - 1 or False
                        ))
                if package_for_picking:
                    package_values.append(package_for_picking)

            _logger.info("Create lots (%d) for pickings to validate" % len(lot_values))
            lots = self.env["stock.production.lot"].create(lot_values)
            _logger.info("Create packages (%d) for pickings to validate" % len(package_values))
            packages = self.env["stock.quant.package"].create(package_values)

            _logger.info("Create sml (%d) for pickings to validate" % len(sml_values))
            for vals in sml_values:
                if vals.get('package_id') is not None:
                    vals['package_id'] = packages[vals['package_id']].id
                if 'lot_id' in vals:
                    vals['lot_id'] = lots[vals['lot_id']].id
            self.env['stock.move.line'].create(sml_values)

            _logger.info("Validate %d of pickings" % len(picking_to_validate))
            picking_to_validate.with_context(skip_backorder=True, skip_sms=True).button_validate()

        # (Un)comment to test a DB with a lot of outgoing/incoming/internal confirmed moves, e.g. for testing of forecasted report
        # pickings = confirm_pickings(0.8)

        # (Un)comment to test a DB with a lot of outgoing/incoming/internal finished moves
        # assign_picking(pickings)
        # validate_pickings(pickings, 1)

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
        product_ids = self.env['product.product'].browse(self.env.registry.populated_models['product.product']).filtered(lambda p: p.type in ('product', 'consu')).ids
        random_products = populate.Random("move_product_sample")
        product_ids = random_products.sample(product_ids, int(len(product_ids) * 0.8))

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
            random = populate.Random('_compute_picking_values')
            for values in iterator:
                if values.get('picking_id'):
                    picking = self.env['stock.picking'].browse(values['picking_id'])
                    values['picking_id'] = picking.id
                    values['location_id'] = picking.location_id.id
                    values['location_dest_id'] = picking.location_dest_id.id
                    values['name'] = picking.name
                    values['date'] = picking.scheduled_date
                    values['company_id'] = picking.company_id.id
                    if picking.picking_type_id.code == 'incoming':
                        values['price_unit'] = random.randint(1, 100)
                yield values

        return [
            ('product_id', populate.randomize(product_ids)),
            ('product_uom', populate.compute(get_product_uom)),
            ('product_uom_qty', populate.randint(1, 10)),
            ('sequence', populate.randint(1, 1000)),
            ('_attach_to_record', _attach_to_record),
            ('_compute_picking_values', _compute_picking_values),
        ]
