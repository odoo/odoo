# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_group_route_so_lines = fields.Boolean(
        'Enable Route on Sales Order Line',
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='sale_stock.group_route_so_lines')

    has_group_display_incoterm = fields.Boolean(
        'Display incoterms on Sales Order and related invoices',
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='sale_stock.group_display_incoterm')
