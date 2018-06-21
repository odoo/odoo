# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    group_website_user = fields.Selection(
        selection=lambda self: self._get_group_selection('base.module_category_website'),
        string='Website Editor', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='base.module_category_website')

    @api.multi
    def _has_unsplash_key_rights(self):
        self.ensure_one()
        if self.has_group('website.group_website_designer'):
            return True
        return super(ResUsers, self)._has_unsplash_key_rights()
