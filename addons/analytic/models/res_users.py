# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_group_analytic_accounting = fields.Boolean(
        'Analytic Accounting', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='analytic.group_analytic_accounting')

    has_group_analytic_tags = fields.Boolean(
        'Analytic Accounting Tags', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='analytic.group_analytic_tags')
