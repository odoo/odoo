# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResGroups(models.Model):
    _inherit = 'res.groups'

    def write(self, vals):
        """ Automatically subscribe new users to linked slide channels """
        write_res = super().write(vals)
        if vals.get('user_ids'):
            # TDE FIXME: maybe directly check users and subscribe them
            # also match channels enrolling groups implied by the written ones
            # (e.g. adding a user to group_user_regular must subscribe them to
            # channels enrolling base.group_user)
            self.env['slide.channel'].sudo().search([('enroll_group_ids', 'in', self.all_implied_ids.ids)])._add_groups_members()
        return write_res
