# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp.osv import osv, fields

class base_config_settings(osv.TransientModel):
    _inherit = 'base.config.settings'

    _columns = {
        'auth_signup_uninvited': fields.boolean('allow public users to sign up', help="If unchecked only invited users may sign up"),
        'auth_signup_template_user_id': fields.many2one('res.users', 'Template user for new users created through signup'),
    }

    #todo: @al, @chs: what is this method for ?
    def get_default_signup(self, cr, uid, fields, context=None):
        icp = self.pool.get('ir.config_parameter')
        return {
            'auth_signup_template_user_id': icp.get_param(cr, uid, 'auth.signup_template_user_id', 0) or False
        }

    #todo: @al, @chs: what is this method for ?
    def set_signup(self, cr, uid, ids, context=None):
        config = self.browse(cr, uid, ids[0], context=context)
        icp = self.pool.get('ir.config_parameter')
        icp.set_param(cr, uid, 'auth.signup_template_user_id', config.auth_signup_template_user_id.id)

    def _get_default_template_user(self, cr, uid, context=None):
        data_obj = self.pool.get('ir.model.data')
        data_id = data_obj._get_id(cr, uid, 'portal', 'default_template_user')
        return data_obj.browse(cr, uid, data_id).res_id

    _defaults = {
        'auth_signup_template_user_id': _get_default_template_user,
    }
