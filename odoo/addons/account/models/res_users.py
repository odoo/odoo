# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError


class GroupsView(models.Model):
    _inherit = 'res.groups'

    @api.model
    def get_application_groups(self, domain):
        # Overridden in order to remove 'Show Full Accounting Features' and
        # 'Show Full Accounting Features - Readonly' in the 'res.users' form view to prevent confusion
        group_account_user = self.env.ref('account.group_account_user', raise_if_not_found=False)
        if group_account_user and group_account_user.category_id.xml_id == 'base.module_category_hidden':
            domain += [('id', '!=', group_account_user.id)]
        group_account_readonly = self.env.ref('account.group_account_readonly', raise_if_not_found=False)
        if group_account_readonly and group_account_readonly.category_id.xml_id == 'base.module_category_hidden':
            domain += [('id', '!=', group_account_readonly.id)]
        return super().get_application_groups(domain)
