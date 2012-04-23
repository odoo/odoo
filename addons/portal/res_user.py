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

from osv import osv, fields



class res_users(osv.osv):
    _inherit = 'res.users'
    _columns = {
        'partner_id': fields.many2one('res.partner',
            string='Related Partner'),
    }

    def prepare_new_user_data(self, u, wiz, password):
        return {
                    'name': u.name,
                    'login': u.user_email,
                    'password': password,
                    'user_email': u.user_email,
                    'context_lang': u.lang,
                    'share': True,
                    'partner_id': u.partner_id and u.partner_id.id,
                } 


res_users()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
