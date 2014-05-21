# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2011 OpenERP S.A. <http://openerp.com>
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

class calendar_contacts(osv.osv):
    _name = 'calendar.contacts'    

    _columns = {
        'user_id': fields.many2one('res.users','Me'),
        'partner_id': fields.many2one('res.partner','Employee',required=True, domain=[]),
        'active':fields.boolean('active'),        
     }
    _defaults = {
        'user_id': lambda self, cr, uid, ctx: uid,
        'active' : True,        
    }