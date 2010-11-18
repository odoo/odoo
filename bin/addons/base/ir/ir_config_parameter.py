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
A module to store some configuration parameters relative to a whole database.
"""

from osv import osv,fields

class ir_config_parameter(osv.osv):
    """ An osv to old configuration parameters for a given database.
    
    To be short, it's just a global dictionnary of strings stored in a table. """
    
    _name = 'ir.config_parameter'
    
    _columns = {
        # The key of the configuration parameter.
        'key': fields.char('Key', size=256, required=True, select=1),
        # The value of the configuration parameter.
        'value': fields.text('Value', required=True),
    }
    
    _sql_constraints = [
        ('key_uniq', 'unique (key)', 'Key must be unique.')
    ]

    def get_param(self, cr, uid, key, context=None):
        """ Get the value of a parameter.
        
        @param key: The key of the parameter.
        @type key: string
        @return: The value of the parameter, False if it does not exist.
        @rtype: string
        """
        ids = self.search(cr, uid, [('key','=',key)], context=context)
        if not ids:
            return False
        param = self.browse(cr, uid, ids[0], context=context)
        value = param.value
        return value
    
    def set_param(self, cr, uid, key, value, context=None):
        """ Set the value of a parameter.
        
        @param key: The key of the parameter.
        @type key: string
        @param value: The value of the parameter.
        @type value: string
        @return: Return the previous value of the parameter of False if it did
        not existed.
        @rtype: string
        """
        ids = self.search(cr, uid, [('key','=',key)], context=context)
        if ids:
            param = self.browse(cr, uid, ids[0], context=context)
            old = param.value
            self.write(cr, uid, ids, {'value': value}, context=context)
            return old
        else:
            self.create(cr, uid, {'key': key, 'value': value}, context=context)
            return False

ir_config_parameter()
