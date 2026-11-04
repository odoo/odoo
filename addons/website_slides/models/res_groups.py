# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class UserGroup(models.Model):
    _inherit = 'res.groups'

    def write(self, vals):
        """ Automatically subscribe new users to linked slide channels """
        write_res = super(UserGroup, self).write(vals)
        if vals.get('users'):
            # TDE FIXME: maybe directly check users and subscribe them
            self.env['slide.channel'].sudo().search([('enroll_group_ids', 'in', self._ids)])._add_groups_members()
        return write_res
