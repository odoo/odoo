# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    def read(self, fields=None, load='_classic_read'):
        # as `pos_blackbox_be` is a certified module, it's hard to make fixes in it
        # so this is a workaround to remove `insz_or_bis_number` field from the fields list
        # as the parent hr.employee model will attempt to read it from hr.employee.public
        # where it doesn't exist
        if fields and 'insz_or_bis_number' in fields:
            pos_blackbox_be_installed = self.env['ir.module.module'].sudo().search_count([('name', '=', 'pos_blackbox_be'), ('state', '=', 'installed')])
            has_hr_user_group = self.env.user.has_group('hr.group_hr_user')
            if pos_blackbox_be_installed and not has_hr_user_group:
                fields.remove('insz_or_bis_number')

        return super().read(fields=fields, load=load)
