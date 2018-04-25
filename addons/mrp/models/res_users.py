# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_group_mrp_routings = fields.Boolean(
        'Manage Work Order Operations', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='mrp.group_mrp_routings')

    group_mrp_user = fields.Selection(
        selection=lambda self: self._get_group_selection('base.module_category_manufacturing'),
        string='Manufacturing', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='base.module_category_manufacturing')
