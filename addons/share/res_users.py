# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

class res_groups(osv.osv):
    _name = "res.groups"
    _inherit = 'res.groups'
    _columns = {
        'share': fields.boolean('Share Group', readonly=True,
                    help="Group created to set access rights for sharing data with some users.")
     }
res_groups()

class res_users(osv.osv):
    _name = 'res.users'
    _inherit = 'res.users'
    _columns = {
        'share': fields.boolean('Share User', readonly=True,
                    help="External user with limited access, created only for the purpose of sharing data.")
     }
res_users()
