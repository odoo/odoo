# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Users(models.Model):
    _inherit = 'res.users'

    target_sales_won = fields.Integer('Won in Opportunities Target')
    target_sales_done = fields.Integer('Activities Done Target')

    has_group_use_lead = fields.Boolean(
        'Show Lead Menu', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='crm.group_use_lead')
