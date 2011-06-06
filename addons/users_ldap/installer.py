# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
from osv import fields, osv
import pooler
import tools
import logging
from service import security
import ldap
from ldap.filter import filter_format

class ldap_installer(osv.osv):
    _name = 'ldap.installer'
    _order = 'sequence'
    _rec_name = 'ldap_server'
    _columns = {
        'sequence': fields.integer('Sequence'),
        'company': fields.many2one('res.company', 'Company', required=True,
            ondelete='cascade'),
        'ldap_server': fields.char('LDAP Server address', size=64, required=True),
        'ldap_server_port': fields.integer('LDAP Server port', required=True),
        'ldap_binddn': fields.char('LDAP binddn', size=64, required=True),
        'ldap_password': fields.char('LDAP password', size=64, required=True),
        'ldap_filter': fields.char('LDAP filter', size=64, required=True),
        'ldap_base': fields.char('LDAP base', size=64, required=True),
        'user': fields.many2one('res.users', 'Model User',
            help="Model used for user creation"),
        'create_user': fields.boolean('Create user',
            help="Create the user if not in database"),
    }
    _defaults = {
        'ldap_server': lambda *a: '127.0.0.1',
        'ldap_server_port': lambda *a: 389,
        'sequence': lambda *a: 10,
        'create_user': lambda *a: True,
    }

ldap_installer()
