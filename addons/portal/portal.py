# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 Tiny SPRL (<http://tiny.be>).
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

class portal(osv.osv):
    _name = 'res.portal'
    _description = 'Portal'
    _columns = {
        'name': fields.char(string='Name', size=64, required=True),
        'user_ids': fields.one2many('res.users', 'portal_id', string='Portal users',
            help='Gives the set of users associated to this portal'),
        'group_ids': fields.many2many('res.groups', 'portal_group', 'portal_id', 'group_id',
            string='Groups', help='Users of this portal automatically belong to those groups'),
    }

portal()

class users(osv.osv):
    _name = 'res.users'
    _inherit = 'res.users'
    _columns = {
        'portal_id': fields.many2one('res.portal', string='Portal',
            help='If given, the portal defines customized menu and access rules'),
    }

users()

