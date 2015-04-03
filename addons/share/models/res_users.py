# -*- coding: utf-8 -*-

from openerp import api, fields, models

class ResUsers(models.Model):
    _name = 'res.users'
    _inherit = 'res.users'

    share = fields.Boolean(string='Share User', store=True, compute='_compute_share', help="External user with limited access, created only for the purpose of sharing data.")

    @api.depends('groups_id')
    def _compute_share(self):
        for user in self:
            user.share = not user.sudo(user).has_group('base.group_user')
