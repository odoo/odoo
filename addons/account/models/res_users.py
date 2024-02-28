# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError


class Users(models.Model):
    _inherit = "res.users"

    @api.constrains('groups_id')
    def _check_one_user_type(self):
        super(Users, self)._check_one_user_type()

        g1 = self.env.ref('account.group_show_line_subtotals_tax_included', False)
        g2 = self.env.ref('account.group_show_line_subtotals_tax_excluded', False)

        if not g1 or not g2:
            # A user cannot be in a non-existant group
            return

        for user in self:
            if user._has_multiple_groups([g1.id, g2.id]):
                raise ValidationError(_("A user cannot have both Tax B2B and Tax B2C.\n"
                                        "You should go in General Settings, and choose to display Product Prices\n"
                                        "either in 'Tax-Included' or in 'Tax-Excluded' mode\n"
                                        "(or switch twice the mode if you are already in the desired one)."))


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
