# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
import logging
import string
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
            ('days_to_prepare_mo', populate.randint(1, 4))
        ]


class Warehouse(models.Model):
    _inherit = 'stock.warehouse'

    def _populate_factories(self):
        return super()._populate_factories() + [
            ('manufacture_steps', populate.iterate(['mrp_one_step', 'pbm', 'pbm_sam'], [0.6, 0.2, 0.2])),
            ('manufacture_to_resupply', populate.iterate([True, False], [0.8, 0.2]))
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
                [0.9] + [0.1 / (len(company_ids) or 1.0)] * (len(company_ids))
                # TODO: Inverse the weight, but need to make the bom tree by company (in bom line populate)
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
    _populate_dependencies = ['mrp.bom', 'product.product']

    def _populate_factories(self):
        # TODO: tree of product by company to be more closer to the reality
        boms = self.env['mrp.bom'].search([('id', 'in', self.env.registry.populated_models['mrp.bom'])],
                                          order='sequence, product_id, id')

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
        product_no_manu = self.env['product.product'].browse(
            self.env.registry.populated_models['product.product']) - product_manu
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
                return random.choice(product_manu_ids[index_prod + 1:])
            else:
                return random.choice(product_no_manu_ids)

        def get_product_uom_id(values, counter, random):
            return self.env['product.product'].browse(values['product_id']).uom_id.id

        def get_bom_product_template_attribute_value_ids(values, counter, random):
            if random.random() < 0.2:
                possible = self.env['mrp.bom'].browse(values['bom_id']).possible_product_template_attribute_value_ids
                return random.sample(possible, int(len(possible) * 0.1))
            else:
                return False

        return [
            ('bom_id', populate.iterate(boms.ids)),
            ('sequence', populate.randint(1, 1000)),
            ('product_id', populate.compute(get_product_id)),
            ('product_uom_id', populate.compute(get_product_uom_id)),
            ('product_qty', populate.randint(1, 10)),
            ('bom_product_template_attribute_value_ids', populate.compute(get_bom_product_template_attribute_value_ids))
        ]


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    _populate_sizes = {'small': 20, 'medium': 100, 'large': 1_000}
    _populate_dependencies = ['res.company']

    def _populate(self, size):
        res = super()._populate(size)

        # Set alternative workcenters
        _logger.info("Set alternative workcenters")
        # Valid workcenters by company_id (the workcenter without company can be the alternative of all workcenter)
        workcenters_by_company = defaultdict(OrderedSet)
        for workcenter in res:
            workcenters_by_company[workcenter.company_id.id].add(workcenter.id)
        workcenters_by_company = {company_id: self.env['mrp.workcenter'].browse(workcenters) for company_id, workcenters
                                  in workcenters_by_company.items()}
        workcenters_by_company = {
            company_id: workcenters | workcenters_by_company.get(False, self.env['mrp.workcenter'])
            for company_id, workcenters in workcenters_by_company.items()}

        random = populate.Random('set_alternative_workcenter')
        for workcenter in res:
            nb_alternative = max(random.randint(0, 3), len(workcenters_by_company[workcenter.company_id.id]) - 1)
            if nb_alternative > 0:
                alternatives_workcenter_ids = random.sample(
                    (workcenters_by_company[workcenter.company_id.id] - workcenter).ids, nb_alternative)
                workcenter.alternative_workcenter_ids = [(6, 0, alternatives_workcenter_ids)]

        return res

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models['res.company'][:COMPANY_NB_WITH_STOCK]
        resource_calendar_no_company = self.env.ref('resource.resource_calendar_std').copy({'company_id': False})

        def get_resource_calendar_id(values, counter, random):
            if not values['company_id']:
                return resource_calendar_no_company.id
            return self.env['res.company'].browse(values['company_id']).resource_calendar_id.id

        def get_note(values, counter, random):
            return "<p>" + ''.join(random.choice(string.ascii_letters) for _ in range(100)) + "</p>"

        return [
            ('name', populate.constant("Workcenter - {counter}")),
            ('company_id', populate.iterate(company_ids + [False])),
            ('resource_calendar_id', populate.compute(get_resource_calendar_id)),
            ('active', populate.iterate([True, False], [0.9, 0.1])),
            ('code', populate.constant("W/{counter}")),
            ('default_capacity', populate.iterate([0.5, 1.0, 2.0, 5.0], [0.2, 0.4, 0.2, 0.2])),
            ('sequence', populate.randint(1, 1000)),
            ('color', populate.randint(1, 12)),
            ('costs_hour', populate.randint(5, 25)),
            ('time_start', populate.iterate([0.0, 2.0, 10.0], [0.6, 0.2, 0.2])),
            ('time_stop', populate.iterate([0.0, 2.0, 10.0], [0.6, 0.2, 0.2])),
            ('oee_target', populate.randint(80, 99)),
            ('note', populate.compute(get_note))
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
        workcenters_by_company = {company_id: self.env['mrp.workcenter'].browse(workcenters) for company_id, workcenters
                                  in workcenters_by_company.items()}
        workcenters_by_company = {
            company_id: workcenters | workcenters_by_company.get(False, self.env['mrp.workcenter'])
            for company_id, workcenters in workcenters_by_company.items()}

        def get_company_id(values, counter, random):
            bom = self.env['mrp.bom'].browse(values['bom_id'])
            return bom.company_id.id

        def get_workcenter_id(values, counter, random):
            return random.choice(workcenters_by_company[values['company_id']]).id

        def get_note(values, counter, random):
            return "<p>" + ''.join(random.choice(string.ascii_letters) for _ in range(100)) + "</p>"

        def get_bom_product_template_attribute_value_ids(values, counter, random):
            if random.random() < 0.2:
                possible = self.env['mrp.bom'].browse(values['bom_id']).possible_product_template_attribute_value_ids
                return random.sample(possible, int(len(possible) * 0.1))
            else:
                return False

        return [
            ('active', populate.iterate([True, False], [0.9, 0.1])),
            ('worksheet_type', populate.iterate(['text', 'pdf', 'google_slide'], [0.6, 0.2, 0.2])),
            ('note', populate.compute(get_note)),
            ('bom_id', populate.iterate(boms_ids)),
            (
            'bom_product_template_attribute_value_ids', populate.compute(get_bom_product_template_attribute_value_ids)),
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
    _populate_dependencies = ['mrp.bom', 'mrp.bom.line', 'mrp.routing.workcenter']

    def _populate(self, size):
        res = super()._populate(size)

        # group the byproducts by their bom for computing cost_share
        byproduct_by_bom = defaultdict(list)
        for byproduct in res:
            byproduct_by_bom[byproduct.bom_id].append(byproduct)

        # set random cost_share that are valid
        for bom_id in byproduct_by_bom:
            if random.random() < 0.5:
                cost_share_sum = 0
                for byproduct in byproduct_by_bom[bom_id]:
                    cost = random.uniform(0, 10)
                    cost_share_sum += cost
                    if cost_share_sum > 100:
                        break
                    byproduct.cost_share = cost
        return res

    def _populate_factories(self):
        # Take a subset (50%) of bom to have some of then without any operation
        random = populate.Random('byproduct_subset_bom')
        boms_ids = self.env.registry.populated_models['mrp.bom']
        boms_ids = random.sample(boms_ids, int(len(boms_ids) * 0.5))

        boms = self.env['mrp.bom'].search([('id', 'in', self.env.registry.populated_models['mrp.bom'])],
                                          order='sequence, product_id, id')

        product_manu_ids = OrderedSet()
        for bom in boms:
            if bom.product_id:
                product_manu_ids.add(bom.product_id.id)
            else:
                for product_id in bom.product_tmpl_id.product_variant_ids:
                    product_manu_ids.add(product_id.id)
        product_manu = self.env['product.product'].browse(product_manu_ids)
        # product_no_manu is products which don't have any bom (leaves in the BoM trees)
        product_no_manu = self.env['product.product'].browse(
            self.env.registry.populated_models['product.product']) - product_manu
        product_no_manu_ids = product_no_manu.ids

        def get_product_uom_id(values, counter, random):
            return self.env['product.product'].browse(values['product_id']).uom_id.id

        def get_bom_product_template_attribute_value_ids(values, counter, random):
            if random.random() < 0.2:
                possible = self.env['mrp.bom'].browse(values['bom_id']).possible_product_template_attribute_value_ids
                return random.sample(possible, int(len(possible) * 0.1))
            else:
                return False

        return [
            ('bom_id', populate.iterate(boms_ids)),
            ('product_id', populate.randomize(product_no_manu_ids)),
            ('product_uom_id', populate.compute(get_product_uom_id)),
            ('product_qty', populate.randint(1, 10)),
            ('bom_product_template_attribute_value_ids', populate.compute(get_bom_product_template_attribute_value_ids))
        ]


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    _populate_sizes = {'small': 100, 'medium': 1_000, 'large': 10_000}
    _populate_dependencies = ['mrp.routing.workcenter', 'mrp.bom.line', 'res.company', 'res.users',
                              'product.product', 'stock.picking.type', 'stock.warehouse.orderpoint', 'procurement.group']

    def _populate(self, size):
        productions = super()._populate(size)

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
        manu_picking_types_by_company_id = {company_id: list(picking_ids) for company_id, picking_ids in
                                            manu_picking_types_by_company_id.items()}

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

        def get_random_text(values, counter, random):
            return ''.join(random.choice(string.ascii_letters) for _ in range(100))

        def get_user_id(values, counter, random):
            return random.choice(
                self.env['res.users'].search([('groups_id', 'in', self.env.ref('mrp.group_mrp_user').id)])).id

        def get_procurement_group_id(values, counter, random):
            groups = random.choice(self.env['procurement.group'].search([])).id
            if groups:
                return random.choice(self.env['procurement.group'].search([])).id
            return False

        def get_orderpoint_id(values, counter, random):
            return random.choice(self.env['stock.warehouse.orderpoint'].search([])).id

        return [
            ('name', populate.constant("MO - {counter}")),
            ('origin', populate.compute(get_random_text)),
            ('qty_producing', populate.randint(0, 5)),
            ('user_id', populate.compute(get_user_id)),
            ('procurement_group_id', populate.compute(get_procurement_group_id)),
            ('product_description_variants', populate.compute(get_random_text)),
            ('orderpoint_id', populate.compute(get_orderpoint_id)),
            ('propagate_cancel', populate.iterate([False, True], [0.8, 0.2])),
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
            ('state', populate.iterate([False, 'done'], [0.9, 0.1]))
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


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    _populate_sizes = {'small': 500, 'medium': 10_000, 'large': 100_000}
    _populate_dependencies = ['res.company', 'stock.move', 'mrp.workorder', 'mrp.production']

    def _populate(self, size):
        lines = super()._populate(size)

        for line in lines:
            line.workorder_id = random.choice(self.env['mrp.workorder'].search(['|', ('company_id', '=', False), ('company_id', '=', line.company_id)])).id
            line.production_id = random.choice(self.env['mrp.production'].search(['|', ('company_id', '=', False), ('company_id', '=', line.company_id)])).id

        return lines


class StockScrap(models.Model):
    _inherit = 'stock.scrap'
    _populate_dependencies = ['mrp.production', 'mrp.workorder']

    def _populate(self, size):
        scraps = super()._populate(size)

        for scrap in scraps:
            scrap.production_id = random.choice(self.env['mrp.production'].search(['|', ('company_id', '=', False), ('company_id', '=', scrap.company_id)])).id
            scrap.workorder_id = random.choice(self.env['mrp.workorder'].search(['|', ('company_id', '=', False), ('company_id', '=', scrap.company_id)])).id

        return scraps


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    _populate_dependencies = ['mrp.bom', 'product.product', 'product.supplierinfo', 'stock.location', 'stock.warehouse']

    def _populate_factories(self):
        def get_bom_id(values, counter, random):
            product_template_id = self.env['product.product'].browse(values['product_id']).product_tmpl_id.id
            boms = self.env['mrp.bom'].search(
                [('type', '=', 'normal'), '&', '|', ('company_id', '=', values['company_id']),
                 ('company_id', '=', False), '|', ('product_id', '=', values['product_id']), '&',
                 ('product_id', '=', False), ('product_tmpl_id', '=', product_template_id)])
            if boms:
                return random.choice(boms).id
            return False

        return super()._populate_factories() + [
            ('bom_id', populate.compute(get_bom_id)),
            ('manufacturing_visibility_days', populate.iterate([0, 1, 2], [0.8, 0.1, 0.1]))
        ]


class WorkcenterTag(models.Model):
    _inherit = 'mrp.workcenter.tag'

    def _populate_factories(self):
        return [
            ('name', populate.constant("Workcenter Tag - {counter}"))
        ]


class MrpWorkcenterProductivityLossType(models.Model):
    _inherit = 'mrp.workcenter.productivity.loss.type'

    def _populate_factories(self):
        return [
            ('loss_type', populate.iterate(['availability', 'performance', 'quality', 'productive']))
        ]


class MrpWorkcenterProductivityLoss(models.Model):
    _inherit = 'mrp.workcenter.productivity.loss'

    _populate_dependencies = ['mrp.workcenter.productivity.loss.type']

    def _populate_factories(self):
        def get_loss_id(values, counter, random):
            return random.choice(self.env['mrp.workcenter.productivity.loss.type'].search(
                [('loss_type', 'in', ['quality', 'availability'])])).id

        return [
            ('name', populate.constant("Workcenter Productivity Loss - {counter}")),
            ('sequence', populate.randint(1, 1000)),
            ('manual', populate.iterate([True, False])),
            ('loss_id', populate.compute(get_loss_id))
        ]


class MrpWorkcenterProductivity(models.Model):
    _inherit = 'mrp.workcenter.productivity'

    _populate_dependencies = ['mrp.workcenter.productivity.loss.type', 'mrp.workcenter', 'mrp.workorder', 'res.company', 'res.users']

    def _populate_factories(self):
        def get_loss_id(values, counter, random):
            return random.choice(self.env['mrp.workcenter.productivity.loss.type'].search([])).id

        def get_workcenter_id(values, counter, random):
            return random.choice(self.env['mrp.workcenter'].search(['|', ('company_id', '=', False), ('company_id', '=', values['company_id'])])).id

        def get_workorder_id(values, counter, random):
            return random.choice(self.env['mrp.workorder'].search(['|', ('company_id', '=', False), ('company_id', '=', values['company_id'])])).id

        def get_company_id(values, counter, random):
            return random.choice(self.env.registry.populated_models['res.company'][:COMPANY_NB_WITH_STOCK])

        def get_user_id(values, counter, random):
            return random.choice(self.env['res.users'].search([])).id

        def get_description(values, counter, random):
            return ''.join(random.choice(string.ascii_letters) for _ in range(100))

        return [
            ('company_id', populate.compute(get_company_id)),
            ('workcenter_id', populate.compute(get_workcenter_id)),
            ('workorder_id', populate.compute(get_workorder_id)),
            ('user_id', populate.compute(get_user_id)),
            ('loss_id', populate.compute(get_loss_id)),
            ('description', populate.compute(get_description))
        ]


class MrpWorkCenterCapacity(models.Model):
    _inherit = 'mrp.workcenter.capacity'

    _populate_dependencies = ['mrp.workcenter', 'product.product']

    def _populate_factories(self):
        def get_workcenter_id(values, counter, random):
            return random.choice(self.env['mrp.workcenter'].search([])).id

        def get_product_id(values, counter, random):
            return random.choice(self.env['product.product'].search([])).id

        return [
            ('workcenter_id', populate.compute(get_workcenter_id)),
            ('product_id', populate.compute(get_product_id)),
            ('capacity', populate.iterate([1, 2, 3], [0.6, 0.2, 0.2]))
        ]


class MrpUnbuild(models.Model):
    _inherit = 'mrp.unbuild'

    _populate_dependencies = ['product.product', 'mrp.bom', 'mrp.production', 'res.company', 'stock.lot']

    def _populate_factories(self):
        def get_product_id(values, counter, random):
            return self.env['mrp.bom'].browse(values['bom_id']).product_id.id

        def get_bom_id(values, counter, random):
            return random.choice(self.env['mrp.bom'].search([
                ('product_id', '!=', False),
                ('type', '=', 'normal'),
                '|',
                    ('company_id', '=', values['company_id']),
                    ('company_id', '=', False)
            ])).id

        def get_company_id(values, counter, random):
            return random.choice(self.env.registry.populated_models['res.company'][:COMPANY_NB_WITH_STOCK])

        def get_mo_id(values, counter, random):
            production = self.env['mrp.production'].search([
                ('state', '=', 'done'),
                ('company_id', '=', values['company_id']),
                ('product_id', '=?', values['product_id']),
                ('bom_id', '=?', values['bom_id'])])
            if production:
                return random.choice(production).id
            return False

        def get_lot_id(values, counter, random):
            lots = self.env['stock.lot'].search([('product_id', '=', values['product_id'])])
            if lots:
                return random.choice(lots).id
            return False

        return [
            ('company_id', populate.compute(get_company_id)),
            ('name', populate.constant("Unbuild Order - {counter}")),
            ('bom_id', populate.compute(get_bom_id)),
            ('product_id', populate.compute(get_product_id)),
            ('product_qty', populate.randint(1, 20)),
            ('mo_id', populate.compute(get_mo_id)),
            ('lot_id', populate.compute(get_lot_id)),
            ('state', populate.iterate(['draft', 'done'], [0.8, 0.2]))
        ]


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    _populate_dependencies = ['mrp.workcenter', 'mrp.production', 'mrp.routing.workcenter',
                              'uom.uom', 'resource.calendar.leaves']

    def _populate_factories(self):
        def get_workcenter_id(values, counter, random):
            company_id = self.env['mrp.production'].browse(values['production_id']).company_id.id
            return random.choice(self.env['mrp.workcenter'].search(['|', ('company_id', '=', False), ('company_id', '=', company_id)])).id

        def get_product_uom_id(values, counter, random):
            return random.choice(self.env['uom.uom'].search([])).id

        def get_production_id(values, counter, random):
            return random.choice(self.env['mrp.production'].search([])).id

        def get_leave_id(values, counter, random):
            company_id = self.env['mrp.production'].browse(values['production_id']).company_id.id
            leaves = self.env['resource.calendar.leaves'].search(['|', ('company_id', '=', False), ('company_id', '=', company_id)])
            if leaves:
                return random.choice(leaves).id
            return False

        def get_operation_id(values, counter, random):
            company_id = self.env['mrp.production'].browse(values['production_id']).company_id.id
            return random.choice(self.env['mrp.routing.workcenter'].search(['|', ('company_id', '=', False), ('company_id', '=', company_id)])).id

        return [
            ('production_id', populate.compute(get_production_id)),
            ('name', populate.constant("Work Order - {counter}")),
            ('workcenter_id', populate.compute(get_workcenter_id)),
            ('product_uom_id', populate.compute(get_product_uom_id)),
            ('qty_produced', populate.randint(0, 5)),
            ('leave_id', populate.compute(get_leave_id)),
            ('operation_id', populate.compute(get_operation_id)),
            ('costs_hour', populate.randfloat(0, 100)),
            ('qty_reported_from_previous_wo', populate.randfloat(0, 10))
        ]


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _populate(self, size):
        rules = super()._populate(size)

        for rule in rules:
            if random.random() < 0.5:
                rule.action = 'manufacture'
        return rules


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    def _populate(self, size):
        picking_types = super()._populate(size)

        picking_types[: random.randint(0, len(picking_types) // 2)].write({
            'code': 'mrp_operation',
            'use_create_components_lots': random.choice([False, True])
        })

        for picking_type in picking_types:
            if not picking_type.default_location_src_id:
                picking_type.default_location_src_id = random.choice(self.env['stock.location'].search(['|', ('company_id', '=', False), ('company_id', '=', picking_type.company_id.id)])).id
            if not picking_type.default_location_dest_id:
                if picking_type.code == 'mrp_operation':
                    picking_type.default_location_dest_id = random.choice(
                        self.env['stock.location'].search(['&', ('scrap_location', '=', False), '|', ('company_id', '=', False), ('company_id', '=', picking_type.company_id.id)])).id
                else:
                    picking_type.default_location_dest_id = random.choice(self.env['stock.location'].search(['|', ('company_id', '=', False), ('company_id', '=', picking_type.company_id.id)])).id

        return picking_types
