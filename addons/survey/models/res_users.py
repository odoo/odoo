# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    group_survey_user = fields.Selection(
        selection=lambda self: self._get_group_selection('base.module_category_survey'),
        string='Survey', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='base.module_category_survey')
