# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, data):
        user = super(ResUsers, self).create(data)
        NoteStage = self.env['note.stage']
        if self.has_group('base.group_user'):
            for n in range(5):
                xmlid = 'note_stage_%02d' % (n,)
                try:
                    stage_id = self.sudo().env.ref('note.' + xmlid).id
                except ValueError:
                    continue
                NoteStage.sudo().copy(stage_id, default={'user_id': self.env.uid})
        return user
