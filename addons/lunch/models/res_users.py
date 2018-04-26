# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    group_lunch_user = fields.Selection(
        selection=lambda self: self._get_group_selection('lunch.module_lunch_category'),
        string='Lunch', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='lunch.module_lunch_category')
