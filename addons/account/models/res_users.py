from odoo import models, _, api


class Users(models.Model):
    _inherit = 'res.users'

    @api.constrains('groups_id')
    def _group_needed_for_settings(self, msg_list=[]):
        group_needed = self.env.ref('account.group_account_manager')
        if group_needed.id not in self.groups_id.ids:
            msg_list.append(_('This user must have the group "%s" for the module Invoicing/Accouting') % group_needed.name)
        super(Users, self)._group_needed_for_settings(msg_list)
