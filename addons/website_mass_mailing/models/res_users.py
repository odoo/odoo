# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_group_website_popup_on_exit = fields.Boolean(
        'Use subscription pop up on the website',
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='website_mass_mailing.group_website_popup_on_exit')
