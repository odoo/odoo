# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime, timedelta
from collections import defaultdict

from odoo import models
from odoo.tools import populate, OrderedSet
from odoo.addons.stock.populate.stock import COMPANY_NB_WITH_STOCK

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _populate_factories(self):
        return super()._populate_factories() + [
            ('manufacturing_lead', populate.randint(0, 2)),
        ]


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _populate_factories(self):
        return super()._populate_factories() + [
            ('produce_delay', populate.randint(1, 4)),
        ]


class Warehouse(models.Model):
    _inherit = 'stock.warehouse'

    def _populate_factories(self):
        return super()._populate_factories() + [
            ('manufacture_steps', populate.iterate(['mrp_one_step', 'pbm', 'pbm_sam'], [0.6, 0.2, 0.2]))
        ]


# TODO : stock picking type manufacturing


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    _populate_sizes = {'small': 100, 'medium': 2_000, 'large': 20_000}
    _populate_dependencies = ['product.product', 'stock.location']

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models['res.company'][:COMPANY_NB_WITH_STOCK]

        product_tmpl_ids = self.env['product.product'].search([
            ('id', 'in', self.env.registry.populated_models['product.product']),
            ('type', 'in', ('product', 'consu'))
        ]).product_tmpl_id.ids
        # Use only a 80 % subset of the products - the 20 % remaining will leaves of the bom tree
        random = populate.Random('subset_product_bom')
        product_tmpl_ids = random.sample(product_tmpl_ids, int(len(product_tmpl_ids) * 0.8))

        def get_product_id(values=None, random=None, **kwargs):
            if random.random() > 0.5:  # 50 % change to target specific product.product
                return False
            return random.choice(self.env['product.template'].browse(values['product_tmpl_id']).product_variant_ids.ids)

        return [
            ('company_id', populate.randomize(
                [False] + company_ids,
                [0.9] + [0.1 / (len(company_ids) or 1.0)] * (len(company_ids))  # TODO: Inverse the weight, but need to make the bom tree by company (in bom line populate)
            )),
            ('product_tmpl_id', populate.randomize(product_tmpl_ids)),
            ('product_id', populate.compute(get_product_id)),
            ('product_qty', populate.randint(1, 5)),
            ('sequence', populate.randint(1, 1000)),
            ('code', populate.constant("R{counter}")),
            ('ready_to_produce', populate.randomize(['all_available', 'asap'])),
        ]


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    _populate_sizes = {'small': 500, 'medium': 10_000, 'large': 100_000}
    _populate_dependencies = ['mrp.bom']

    def _populate_factories(self):
        # TODO: tree of product by company to be more closer to the reality
        boms = self.env['mrp.bom'].search([('id', 'in', self.env.registry.populated_models['mrp.bom'])], order='sequence, product_id, id')

        product_manu_ids = OrderedSet()
        for bom in boms:
            if bom.product_id:
                product_manu_ids.add(bom.product_id.id)
            else:
                for product_id in bom.product_tmpl_id.product_variant_ids:
                    product_manu_ids.add(product_id.id)
        product_manu_ids = list(product_manu_ids)
        product_manu = self.env['product.product'].browse(product_manu_ids)
        # product_no_manu is products which don't have any bom (leaves in the BoM trees)
        product_no_manu = self.env['product.product'].browse(self.env.registry.populated_models['product.product']) - product_manu
        product_no_manu_ids = product_no_manu.ids

        def get_product_id(values, counter, random):
            bom = self.env['mrp.bom'].browse(values['bom_id'])
            last_product_bom = bom.product_id if bom.product_id else bom.product_tmpl_id.product_variant_ids[-1]
            # TODO: index in list is in O(n) can be avoid by a cache dict (if performance issue)
            index_prod = product_manu_ids.index(last_product_bom.id)
            # Always choose a product futher in the recordset `product_manu` to avoid any loops
            # Or used a product in the `product_no_manu`

            sparsity = 0.4  # Increase the sparsity will decrease the density of the BoM trees => smaller Tree

            len_remaining_manu = len(product_manu_ids) - index_prod - 1
            len_no_manu = len(product_no_manu_ids)
            threshold = len_remaining_manu / (len_remaining_manu + sparsity * len_no_manu)
            if random.random() <= threshold:
                # TODO: avoid copy the list (if performance issue)
                return random.choice(product_manu_ids[index_prod+1:])
            else:
                return random.choice(product_no_manu_ids)

        def get_product_uom_id(values, counter, random):
            return self.env['product.product'].browse(values['product_id']).uom_id.id

        return [
            ('bom_id', populate.iterate(boms.ids)),
            ('sequence', populate.randint(1, 1000)),
            ('product_id', populate.compute(get_product_id)),
            ('product_uom_id', populate.compute(get_product_uom_id)),
            ('product_qty', populate.randint(1, 10)),
        ]


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    _populate_sizes = {'small': 20, 'medium': 100, 'large': 1_000}

    def _populate(self, size):
        res = super()._populate(size)

        # Set alternative workcenters
        _logger.info("Set alternative workcenters")
        # Valid workcenters by company_id (the workcenter without company can be the alternative of all workcenter)
        workcenters_by_company = defaultdict(OrderedSet)
        for workcenter in res:
            workcenters_by_company[workcenter.company_id.id].add(workcenter.id)
        workcenters_by_company = {company_id: self.env['mrp.workcenter'].browse(workcenters) for company_id, workcenters in workcenters_by_company.items()}
        workcenters_by_company = {
            company_id: workcenters | workcenters_by_company.get(False, self.env['mrp.workcenter'])
            for company_id, workcenters in workcenters_by_company.items()}

        random = populate.Random('set_alternative_workcenter')
        for workcenter in res:
            nb_alternative = max(random.randint(0, 3), len(workcenters_by_company[workcenter.company_id.id]) - 1)
            if nb_alternative > 0:
                alternatives_workcenter_ids = random.sample((workcenters_by_company[workcenter.company_id.id] - workcenter).ids, nb_alternative)
                workcenter.alternative_workcenter_ids = [(6, 0, alternatives_workcenter_ids)]

        return res

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models['res.company'][:COMPANY_NB_WITH_STOCK]
        resource_calendar_no_company = self.env.ref('resource.resource_calendar_std').copy({'company_id': False})

        def get_resource_calendar_id(values, counter, random):
            if not values['company_id']:
                return resource_calendar_no_company.id
            return self.env['res.company'].browse(values['company_id']).resource_calendar_id.id

        return [
            ('name', populate.constant("Workcenter - {counter}")),
            ('company_id', populate.iterate(company_ids + [False])),
            ('resource_calendar_id', populate.compute(get_resource_calendar_id)),
            ('active', populate.iterate([True, False], [0.9, 0.1])),
            ('code', populate.constant("W/{counter}")),
            ('capacity', populate.iterate([0.5, 1.0, 2.0, 5.0], [0.2, 0.4, 0.2, 0.2])),
            ('sequence', populate.randint(1, 1000)),
            ('color', populate.randint(1, 12)),
            ('costs_hour', populate.randint(5, 25)),
            ('time_start', populate.iterate([0.0, 2.0, 10.0], [0.6, 0.2, 0.2])),
            ('time_stop', populate.iterate([0.0, 2.0, 10.0], [0.6, 0.2, 0.2])),
            ('oee_target', populate.randint(80, 99)),
        ]


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    _populate_sizes = {'small': 500, 'medium': 5_000, 'large': 50_000}
    _populate_dependencies = ['mrp.workcenter', 'mrp.bom']

    def _populate_factories(self):
        # Take a subset (70%) of bom to have some of then without any operation
        random = populate.Random('operation_subset_bom')
        boms_ids = self.env.registry.populated_models['mrp.bom']
        boms_ids = random.sample(boms_ids, int(len(boms_ids) * 0.7))

        # Valid workcenters by company_id (the workcenter without company can be used by any operation)
        workcenters_by_company = defaultdict(OrderedSet)
        for workcenter in self.env['mrp.workcenter'].browse(self.env.registry.populated_models['mrp.workcenter']):
            workcenters_by_company[workcenter.company_id.id].add(workcenter.id)
        workcenters_by_company = {company_id: self.env['mrp.workcenter'].browse(workcenters) for company_id, workcenters in workcenters_by_company.items()}
        workcenters_by_company = {
            company_id: workcenters | workcenters_by_company.get(False, self.env['mrp.workcenter'])
            for company_id, workcenters in workcenters_by_company.items()}

        def get_company_id(values, counter, random):
            bom = self.env['mrp.bom'].browse(values['bom_id'])
            return bom.company_id.id

        def get_workcenter_id(values, counter, random):
            return random.choice(workcenters_by_company[values['company_id']]).id

        return [
            ('bom_id', populate.iterate(boms_ids)),
            ('company_id', populate.compute(get_company_id)),
            ('workcenter_id', populate.compute(get_workcenter_id)),
            ('name', populate.constant("OP-{counter}")),
            ('sequence', populate.randint(1, 1000)),
            ('time_mode', populate.iterate(['auto', 'manual'])),
            ('time_mode_batch', populate.randint(1, 100)),
            ('time_cycle_manual', populate.randomize([1.0, 15.0, 60.0, 1440.0])),
        ]


class MrpBomByproduct(models.Model):
    _inherit = 'mrp.bom.byproduct'

    _populate_sizes = {'small': 50, 'medium': 1_000, 'large': 5_000}
    _populate_dependencies = ['mrp.bom.line', 'mrp.routing.workcenter']

    def _populate_factories(self):
        # Take a subset (50%) of bom to have some of then without any operation
        random = populate.Random('byproduct_subset_bom')
        boms_ids = self.env.registry.populated_models['mrp.bom']
        boms_ids = random.sample(boms_ids, int(len(boms_ids) * 0.5))

        boms = self.env['mrp.bom'].search([('id', 'in', self.env.registry.populated_models['mrp.bom'])], order='sequence, product_id, id')

        product_manu_ids = OrderedSet()
        for bom in boms:
            if bom.product_id:
                product_manu_ids.add(bom.product_id.id)
            else:
                for product_id in bom.product_tmpl_id.product_variant_ids:
                    product_manu_ids.add(product_id.id)
        product_manu = self.env['product.product'].browse(product_manu_ids)
        # product_no_manu is products which don't have any bom (leaves in the BoM trees)
        product_no_manu = self.env['product.product'].browse(self.env.registry.populated_models['product.product']) - product_manu
        product_no_manu_ids = product_no_manu.ids

        def get_product_uom_id(values, counter, random):
            return self.env['product.product'].browse(values['product_id']).uom_id.id

        return [
            ('bom_id', populate.iterate(boms_ids)),
            ('product_id', populate.randomize(product_no_manu_ids)),
            ('product_uom_id', populate.compute(get_product_uom_id)),
            ('product_qty', populate.randint(1, 10)),
        ]


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    _populate_sizes = {'small': 100, 'medium': 1_000, 'large': 10_000}
    _populate_dependencies = ['mrp.routing.workcenter', 'mrp.bom.line']

    def _populate(self, size):
        productions = super()._populate(size)

        def fill_mo_with_bom_info():
            productions_with_bom = productions.filtered('bom_id')
            _logger.info("Create Raw moves of MO(s) with bom (%d)" % len(productions_with_bom))
            self.env['stock.move'].create(productions_with_bom._get_moves_raw_values())
            _logger.info("Create Finished moves of MO(s) with bom (%d)" % len(productions_with_bom))
            self.env['stock.move'].create(productions_with_bom._get_moves_finished_values())
            _logger.info("Create Workorder moves of MO(s) with bom (%d)" % len(productions_with_bom))
            productions_with_bom._create_workorder()

        fill_mo_with_bom_info()

        def confirm_bom_mo(sample_ratio):
            # Confirm X % of prototype MO
            random = populate.Random('confirm_bom_mo')
            mo_ids = productions.filtered('bom_id').ids
            mo_to_confirm = self.env['mrp.production'].browse(random.sample(mo_ids, int(len(mo_ids) * 0.8)))
            _logger.info("Confirm %d MO with BoM" % len(mo_to_confirm))
            mo_to_confirm.action_confirm()

        # Uncomment this line to confirm a part of MO, can be useful to check performance
        # confirm_bom_mo(0.8)

        return productions

    def _populate_factories(self):
        now = datetime.now()
        company_ids = self.env.registry.populated_models['res.company'][:COMPANY_NB_WITH_STOCK]

        products = self.env['product.product'].browse(self.env.registry.populated_models['product.product'])
        product_ids = products.filtered(lambda product: product.type in ('product', 'consu')).ids

        boms = self.env['mrp.bom'].browse(self.env.registry.populated_models['mrp.bom'])
        boms_by_company = defaultdict(OrderedSet)
        for bom in boms:
            boms_by_company[bom.company_id.id].add(bom.id)
        boms_by_company = {company_id: self.env['mrp.bom'].browse(boms) for company_id, boms in boms_by_company.items()}
        boms_by_company = {
            company_id: boms | boms_by_company.get(False, self.env['mrp.bom'])
            for company_id, boms in boms_by_company.items()}

        def get_bom_id(values, counter, random):
            if random.random() > 0.7:  # 30 % of prototyping
                return False
            return random.choice(boms_by_company[values['company_id']]).id

        def get_consumption(values, counter, random):
            if not values['bom_id']:
                return 'flexible'
            return self.env['mrp.bom'].browse(values['bom_id']).consumption

        def get_product_id(values, counter, random):
            if not values['bom_id']:
                return random.choice(product_ids)
            bom = self.env['mrp.bom'].browse(values['bom_id'])
            return bom.product_id.id or random.choice(bom.product_tmpl_id.product_variant_ids.ids)

        def get_product_uom_id(values, counter, random):
            product = self.env['product.product'].browse(values['product_id'])
            return product.uom_id.id

        # Fetch all stock picking type and group then by company_id
        manu_picking_types = self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')])
        manu_picking_types_by_company_id = defaultdict(OrderedSet)
        for picking_type in manu_picking_types:
            manu_picking_types_by_company_id[picking_type.company_id.id].add(picking_type.id)
        manu_picking_types_by_company_id = {company_id: list(picking_ids) for company_id, picking_ids in manu_picking_types_by_company_id.items()}

        def get_picking_type_id(values, counter, random):
            return random.choice(manu_picking_types_by_company_id[values['company_id']])

        def get_location_src_id(values, counter, random):
            # TODO : add some randomness
            picking_type = self.env['stock.picking.type'].browse(values['picking_type_id'])
            return picking_type.default_location_src_id.id

        def get_location_dest_id(values, counter, random):
            # TODO : add some randomness
            picking_type = self.env['stock.picking.type'].browse(values['picking_type_id'])
            return picking_type.default_location_dest_id.id

        def get_date_planned_start(values, counter, random):
            # 95.45 % of picking scheduled between (-10, 30) days and follow a gauss distribution (only +-15% picking is late)
            delta = random.gauss(10, 10)
            return now + timedelta(days=delta)

        return [
            ('company_id', populate.iterate(company_ids)),
            ('bom_id', populate.compute(get_bom_id)),
            ('consumption', populate.compute(get_consumption)),
            ('product_id', populate.compute(get_product_id)),
            ('product_uom_id', populate.compute(get_product_uom_id)),
            ('product_qty', populate.randint(1, 10)),
            ('picking_type_id', populate.compute(get_picking_type_id)),
            ('date_planned_start', populate.compute(get_date_planned_start)),
            ('location_src_id', populate.compute(get_location_src_id)),
            ('location_dest_id', populate.compute(get_location_dest_id)),
            ('priority', populate.iterate(['0', '1'], [0.95, 0.05])),
        ]


class StockMove(models.Model):
    _inherit = 'stock.move'

    _populate_dependencies = ['stock.picking', 'mrp.production']

    def _populate(self, size):
        moves = super()._populate(size)

        def confirm_prototype_mo(sample_ratio):
            # Confirm X % of prototype MO
            random = populate.Random('confirm_prototype_mo')
            mo_ids = moves.raw_material_production_id.ids
            mo_to_confirm = self.env['mrp.production'].browse(random.sample(mo_ids, int(len(mo_ids) * 0.8)))
            _logger.info("Confirm %d of prototype MO" % len(mo_to_confirm))
            mo_to_confirm.action_confirm()

        # (Un)comment this line to confirm a part of prototype MO, can be useful to check performance
        # confirm_prototype_mo(0.8)

        return moves.exists()  # Confirm Mo can unlink moves

    def _populate_attach_record_weight(self):
        fields, weight = super()._populate_attach_record_weight()
        return fields + ['raw_material_production_id'], weight + [1]

    def _populate_attach_record_generator(self):

        productions = self.env['mrp.production'].browse(self.env.registry.populated_models['mrp.production'])
        productions = productions.filtered(lambda prod: not prod.bom_id)

        def next_production_id():
            while productions:
                yield from productions.ids

        return {**super()._populate_attach_record_generator(), 'raw_material_production_id': next_production_id()}

    def _populate_factories(self):

        def _compute_production_values(iterator, field_name, model_name):
            for values in iterator:

                if values.get('raw_material_production_id'):
                    production = self.env['mrp.production'].browse(values['raw_material_production_id'])
                    values['location_id'] = production.location_src_id.id
                    values['location_dest_id'] = production.production_location_id.id
                    values['picking_type_id'] = production.picking_type_id.id
                    values['name'] = production.name
                    values['date'] = production.date_planned_start
                    values['company_id'] = production.company_id.id
                yield values

        return super()._populate_factories() + [
            ('_compute_production_values', _compute_production_values),
        ]
