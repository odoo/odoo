# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    group_im_livechat_user = fields.Selection(
        selection=lambda self: self._get_group_selection('im_livechat.module_category_im_livechat'),
        string='Live Support', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='im_livechat.module_category_im_livechat',
        help='User: The user will be able to join support channels.\nManager: The user will be able to delete support channels.')
