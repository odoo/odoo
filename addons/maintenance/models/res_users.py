# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_group_equipment_manager = fields.Boolean(
        'Equipment Manager', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='maintenance.group_equipment_manager',
        help='The user will be able to manage equipments.')
