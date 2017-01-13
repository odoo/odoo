# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Users(models.Model):

    _name = 'res.users'
    _inherit = ['res.users']

    @api.model
    def create(self, values):
        user = super(Users, self).create(values)
        # for new employee, create his own 5 base note stages
        if user.has_group('base.group_user'):
            for num in range(5):
                stage = self.env.ref('note.note_stage_%02d' % (num,), raise_if_not_found=False)
                if stage:
                    stage.sudo().copy(default={'user_id': user.id})
        return user
