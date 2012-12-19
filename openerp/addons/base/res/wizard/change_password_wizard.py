# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 OpenERP S.A (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv

class change_password_wizard(osv.TransientModel):
    """
        A wizard to manage the change of users' passwords
    """
    def _get_user_ids(self, cr, uid, context=None):
        if context == None:
            context = {}
        return context.get('active_ids', [])

    _name = "change.password.wizard"
    _description = "Change Password Wizard"
    _columns = {
        'user_ids': fields.one2many('change.password.user', 'wizard_id', string='Users'),
    }
    _defaults = {
        'user_ids': _get_user_ids,
    }

    def change_password_button(self, cr, uid, ids, context=None):
        user_ids = self.browse(cr, uid, ids[0], context=context).user_ids
        self.pool.get('change.password.user').change_password_button(cr, uid, user_ids, context=context)
        return {
            'type': 'ir.actions.act_window_close',
        }

class change_password_user(osv.TransientModel):
    """
        A model to configure users in the change password wizard
    """



    _name = 'change.password.user'
    _description = 'Change Password Wizard User'
    _columns = {
        'wizard_id': fields.many2one('change.password.wizard', string='Wizard', required=True),
        'user_id': fields.many2one('res.users', string='User', required=True),
        'login': fields.related('user_id', 'login', type='char', relation='res.users', string='User Login', readonly=True),
        'new_passwd': fields.char('New Password', required=True),
        'old_passwd': fields.related('user_id', 'password', type='char', relation='res.users', string='Old Password', readonly=True)
    }
    _defaults = {
    }

    def change_password_button(self, cr, uid, ids, context=None):
        for user in self.browse(cr, uid, ids, context=context):
            self.pool.get('res.users').change_password(cr, uid, user.old_passwd, user.new_passwd, context=context)
