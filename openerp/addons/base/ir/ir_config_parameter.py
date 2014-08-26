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

import uuid
import datetime

from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools import misc, config

"""
A dictionary holding some configuration parameters to be initialized when the database is created.
"""
_default_parameters = {
    "database.uuid": lambda: (str(uuid.uuid1()), []),
    "database.create_date": lambda: (datetime.datetime.now().strftime(misc.DEFAULT_SERVER_DATETIME_FORMAT), ['base.group_user']),
    "web.base.url": lambda: ("http://localhost:%s" % config.get('xmlrpc_port'), []),
}


class ir_config_parameter(osv.osv):
    """Per-database storage of configuration key-value pairs."""

    _name = 'ir.config_parameter'
    _rec_name = 'key'

    _columns = {
        'key': fields.char('Key', required=True, select=1),
        'value': fields.text('Value', required=True),
        'group_ids': fields.many2many('res.groups', 'ir_config_parameter_groups_rel', 'icp_id', 'group_id', string='Groups'),
    }

    _sql_constraints = [
        ('key_uniq', 'unique (key)', 'Key must be unique.')
    ]

    def init(self, cr, force=False):
        """
        Initializes the parameters listed in _default_parameters.
        It overrides existing parameters if force is ``True``.
        """
        for key, func in _default_parameters.iteritems():
            # force=True skips search and always performs the 'if' body (because ids=False)
            ids = not force and self.search(cr, SUPERUSER_ID, [('key','=',key)])
            if not ids:
                value, groups = func()
                self.set_param(cr, SUPERUSER_ID, key, value, groups=groups)


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

    def set_param(self, cr, uid, key, value, groups=[], context=None):
        """Sets the value of a parameter.

        :param string key: The key of the parameter value to set.
        :param string value: The value to set.
        :param list of string groups: List of group (xml_id allowed) to read this key.
        :return: the previous value of the parameter or False if it did
                 not exist.
        :rtype: string
        """
        ids = self.search(cr, uid, [('key','=',key)], context=context)

        gids = []
        for group_xml in groups:
            res_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, group_xml)
            if res_id:
                gids.append((4, res_id))

        vals = {'value': value}
        if gids:
            vals.update(group_ids=gids)
        if ids:
            param = self.browse(cr, uid, ids[0], context=context)
            old = param.value
            self.write(cr, uid, ids, vals, context=context)
            return old
        else:
            vals.update(key=key)
            self.create(cr, uid, vals, context=context)
            return False

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
