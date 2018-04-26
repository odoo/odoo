# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_group_uom = fields.Boolean(
        'Manage Multiple Units of Measure', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='uom.group_uom')
