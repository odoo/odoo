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
"""
A module to handle a database UUID. That uuid will be stored in the osv
"ir.config_parameter" with key "database.uuid".
"""

from osv import osv
import uuid

class uuid_saver(osv.osv_memory):
    """ An empty osv memory to init the uuid of the database the first it is
    used. """
    
    _name = 'pw.database_uuid_saver'
    
    def init(self, cr):
        """ Checks that the database uuid was already created and create it if
        it not the case. """
        params = self.pool.get('ir.config_parameter')
        uniq = params.get_param(cr, 1, 'database.uuid')
        if not uniq:
            uniq = str(uuid.uuid1())
            params.set_param(cr, 1, 'database.uuid', uniq)

uuid_saver()

