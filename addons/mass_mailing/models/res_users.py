# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    group_mass_mailing_user = fields.Selection(
        selection=lambda self: self._get_group_selection('base.module_category_mass_mailing'),
        string='Mass Mailing', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='base.module_category_mass_mailing')

    has_group_mass_mailing_campaign = fields.Boolean(
        'Manage Mass Mailing Campaigns', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='mass_mailing.group_mass_mailing_campaign')
