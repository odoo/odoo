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

class signup_signup(osv.TransientModel):
    _name = 'auth.signup'

    # TODO add captcha
    _columns = {
        'name': fields.char('Name', size=64),
        'email': fields.char('Email', size=64),
        'password': fields.char('Password', size=64),
    }

    def create(self, cr, uid, values, context=None):
        # NOTE here, invalid values raises exceptions to avoid storing
        # sensitive data into the database (which then are available to anyone)

        new_user = {
            'name': values['name'],
            'login': values['email'],
            'email': values['email'],
            'password': values['password'],
            'active': True,
        }

        user_template_id = self.pool.get('ir.config_parameter').get_param(cr, uid, 'auth.signup_template_user_id', 0)
        if user_template_id:
            self.pool.get('res.users').copy(cr, 1, user_template_id, new_user, context=context)
        else:
            self.pool.get('res.users').create(cr, 1, new_user, context=context)

        # Dont store anything
        return 0
