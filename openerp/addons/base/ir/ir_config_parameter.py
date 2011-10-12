# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP SA (<http://www.openerp.com>).
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
Store database-specific configuration parameters
"""

from osv import osv,fields
import uuid
import datetime
from tools import misc

"""
A dictionary holding some configuration parameters to be initialized when the database is created.
"""
_default_parameters = {
    "database.uuid": lambda: str(uuid.uuid1()),
    "database.create_date": lambda: datetime.datetime.now().strftime(misc.DEFAULT_SERVER_DATETIME_FORMAT),
    "web.base.url": lambda: "http://localhost:8069",
}

class ir_config_parameter(osv.osv):
    """Per-database storage of configuration key-value pairs."""

    _name = 'ir.config_parameter'

    _columns = {
        'key': fields.char('Key', size=256, required=True, select=1),
        'value': fields.text('Value', required=True),
    }

    _sql_constraints = [
        ('key_uniq', 'unique (key)', 'Key must be unique.')
    ]

    def init(self, cr):
        """
        Initializes the parameters listed in _default_parameters.
        """
        for key, func in _default_parameters.iteritems():
            ids = self.search(cr, 1, [('key','=',key)])
            if not ids:
                self.set_param(cr, 1, key, func())

    def get_param(self, cr, uid, key, default=False, context=None):
        """Retrieve the value for a given key.

        :param string key: The key of the parameter value to retrieve.
        :param string default: default value if parameter is missing.
        :return: The value of the parameter, or ``default`` if it does not exist.
        :rtype: string
        """
        ids = self.search(cr, uid, [('key','=',key)], context=context)
        if not ids:
            return default
        param = self.browse(cr, uid, ids[0], context=context)
        value = param.value
        return value
    
    def set_param(self, cr, uid, key, value, context=None):
        """Sets the value of a parameter.
        
        :param string key: The key of the parameter value to set.
        :param string value: The value to set.
        :return: the previous value of the parameter or False if it did
                 not exist.
        :rtype: string
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
