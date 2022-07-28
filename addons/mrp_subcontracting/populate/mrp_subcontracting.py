# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from odoo import models
from odoo.tools import populate

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    def _populate(self, size):
        boms = super()._populate(size)
        random.sample(boms, random.randint(0, len(boms) // 2)).write({'type': 'subcontract'})
        return boms

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    _populate_dependencies = ['res.partner']

    def _populate_factories(self):
        def get_subcontractor_id(values, counter, random):
            return random.choice(self.env['res.partner'].search([])).id

        return super()._populate_factories() + [
            ('subcontracting_has_been_recorded', populate.iterate([False, True])),
            ('subcontractor_id', get_subcontractor_id)
        ]

class ResCompany(models.Model):
    _inherit = 'res.company'

    _populate_dependencies = ['stock.location']

    def _populate_factories(self):
        def get_subcontracting_location_id(values, counter, random):
            return random.choice(self.env['stock.location'].search([])).id

        return super()._populate_factories() + [
            ('subcontracting_location_id', get_subcontracting_location_id)
        ]

class ResPartner(models.Model):
    _inherit = 'res.partner'

    _populate_dependencies = ['stock.location']

    def _populate_factories(self):
        def get_property_stock_subcontractor(values, counter, random):
            return random.choice(self.env['stock.location'].search([])).id

        return super()._populate_factories() + [
            ('property_stock_subcontractor', get_property_stock_subcontractor)
        ]

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _populate_factories(self):
        return super()._populate_factories() + [
            ('is_subcontract', populate.iterate([False, True]))
        ]

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _populate_factories(self):
        return super()._populate_factories() + [
            ('is_subcontract', populate.iterate([False, True]))
        ]

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    _populate_dependencies = ['stock.rule', 'stock.route', 'stock.picking.type']

    def _populate_factories(self):
        def get_subcontracting_mto_pull_id(values, counter, random):
            return random.choice(self.env['stock.rule'].search([])).id

        def get_subcontracting_pull_id(values, counter, random):
            return random.choice(self.env['stock.rule'].search([])).id

        def get_subcontracting_route_id(values, counter, random):
            return random.choice(self.env['stock.route'].search([])).id

        def get_subcontracting_type_id(values, counter, random):
            return random.choice(self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')])).id

        def get_subcontracting_resupply_type_id(values, counter, random):
            return random.choice(self.env['stock.picking.type'].search([('code', '=', 'outgoing')])).id

        return super()._populate_factories() + [
            ('subcontracting_to_resupply', populate.iterate([True, False])),
            ('subcontracting_mto_pull_id', get_subcontracting_mto_pull_id),
            ('subcontracting_pull_id', get_subcontracting_pull_id),
            ('subcontracting_route_id', get_subcontracting_route_id),
            ('subcontracting_type_id', get_subcontracting_type_id),
            ('subcontracting_resupply_type_id', get_subcontracting_resupply_type_id)
        ]
