# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _filter_tracking_x2m(self, fname):
        result = super()._filter_tracking_x2m(fname)
        if fname == 'groups_id':
            result += self.env['res.groups'].browse([
                self.env['ir.model.data']._xmlid_to_res_model_res_id('account.group_account_user', False)[1],
                self.env['ir.model.data']._xmlid_to_res_model_res_id('account.group_account_readonly', False)[1],
                self.env['ir.model.data']._xmlid_to_res_model_res_id('account.group_account_basic', False)[1],
                self.env['ir.model.data']._xmlid_to_res_model_res_id('account.group_account_manager', False)[1],
                self.env['ir.model.data']._xmlid_to_res_model_res_id('account.group_account_invoice', False)[1],
                self.env['ir.model.data']._xmlid_to_res_model_res_id('account.group_validate_bank_account', False)[1],
                self.env['ir.model.data']._xmlid_to_res_model_res_id('base.group_system', False)[1],
                self.env['ir.model.data']._xmlid_to_res_model_res_id('base.group_erp_manager', False)[1],
            ])
        return result


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
        group_account_basic = self.env.ref('account.group_account_basic', raise_if_not_found=False)
        if group_account_basic and group_account_basic.category_id.xml_id == 'base.module_category_hidden':
            domain += [('id', '!=', group_account_basic.id)]
        return super().get_application_groups(domain)
