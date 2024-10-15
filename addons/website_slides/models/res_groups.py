# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons import mail


class ResGroups(mail.ResGroups):

    def write(self, vals):
        """ Automatically subscribe new users to linked slide channels """
        write_res = super().write(vals)
        if vals.get('users'):
            # TDE FIXME: maybe directly check users and subscribe them
            self.env['slide.channel'].sudo().search([('enroll_group_ids', 'in', self._ids)])._add_groups_members()
        return write_res
