# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_group_stock_multi_locations = fields.Boolean(
        'Manage Multiple Stock Locations',
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='stock.group_stock_multi_locations')

    has_group_stock_multi_warehouses = fields.Boolean(
        'Manage Multiple Warehouses',
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='stock.group_stock_multi_warehouses')

    has_group_production_lot = fields.Boolean(
        'Manage Lots / Serial Numbers',
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='stock.group_production_lot')

    has_group_lot_on_delivery_slip = fields.Boolean(
        'Display Lots & Serial Numbers on Delivery Slip',
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='stock.group_lot_on_delivery_slip')

    has_group_tracking_lot = fields.Boolean(
        'Manage Packages',
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='stock.group_tracking_lot')

    has_group_adv_location = fields.Boolean(
        'Manage Push and Pull inventory flows',
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='stock.group_adv_location')

    has_group_tracking_owner = fields.Boolean(
        'Manage Different Stock Owners',
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='stock.group_tracking_owner')

    has_group_warning_stock = fields.Boolean(
        'A warning can be set on a partner (Stock)',
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='stock.group_warning_stock')

    group_stock_user = fields.Selection(
        selection=lambda self: self._get_group_selection('base.module_category_warehouse_management'),
        string='Inventory', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='base.module_category_warehouse_management')
