# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID
from openerp.osv import osv, fields

class res_users(osv.Model):
    _name = 'res.users'
    _inherit = ['res.users']
    def create(self, cr, uid, data, context=None):
        user_id = super(res_users, self).create(cr, uid, data, context=context)
        note_obj = self.pool['note.stage']
        data_obj = self.pool['ir.model.data']
        is_employee = self.has_group(cr, user_id, 'base.group_user')
        if is_employee:
            for n in range(5):
                xmlid = 'note_stage_%02d' % (n,)
                try:
                    _model, stage_id = data_obj.get_object_reference(cr, SUPERUSER_ID, 'note', xmlid)
                except ValueError:
                    continue
                note_obj.copy(cr, SUPERUSER_ID, stage_id, default={'user_id': user_id}, context=context)
        return user_id
