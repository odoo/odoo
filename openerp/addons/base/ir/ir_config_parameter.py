# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""
Store database-specific configuration parameters
"""

import uuid
import datetime

from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools import misc, config, ormcache

"""
A dictionary holding some configuration parameters to be initialized when the database is created.
"""
_default_parameters = {
    "database.secret": lambda: (str(uuid.uuid4()), ['base.group_erp_manager']),
    "database.uuid": lambda: (str(uuid.uuid1()), []),
    "database.create_date": lambda: (datetime.datetime.now().strftime(misc.DEFAULT_SERVER_DATETIME_FORMAT), ['base.group_user']),
    "database.expiration_date": lambda: ((datetime.datetime.now()+datetime.timedelta(+30)).strftime(misc.DEFAULT_SERVER_DATETIME_FORMAT), ['base.group_user']),
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
        result = self._get_param(cr, uid, key)
        if result is None:
            return default
        return result

    @ormcache('uid', 'key')
    def _get_param(self, cr, uid, key):
        params = self.search_read(cr, uid, [('key', '=', key)], fields=['value'], limit=1)
        if not params:
            return None
        return params[0]['value']

    def set_param(self, cr, uid, key, value, groups=(), context=None):
        """Sets the value of a parameter.

        :param string key: The key of the parameter value to set.
        :param string value: The value to set.
        :param list of string groups: List of group (xml_id allowed) to read this key.
        :return: the previous value of the parameter or False if it did
                 not exist.
        :rtype: string
        """
        self._get_param.clear_cache(self)
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

    def write(self, cr, uid, ids, vals, context=None):
        self._get_param.clear_cache(self)
        return super(ir_config_parameter, self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        self._get_param.clear_cache(self)
        return super(ir_config_parameter, self).unlink(cr, uid, ids, context=context)