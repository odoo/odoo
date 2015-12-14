# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""
Store database-specific configuration parameters
"""

import uuid
import datetime

from odoo import api, fields, models
from odoo.tools import misc, config, ormcache

"""
A dictionary holding some configuration parameters to be initialized when the database is created.
"""
_default_parameters = {
    "database.secret": lambda: (str(uuid.uuid4()), ['base.group_erp_manager']),
    "database.uuid": lambda: (str(uuid.uuid1()), []),
    "database.create_date": lambda: (datetime.datetime.now().strftime(misc.DEFAULT_SERVER_DATETIME_FORMAT), ['base.group_user']),
    "web.base.url": lambda: ("http://localhost:%s" % config.get('xmlrpc_port'), []),
}


class IrConfigParameter(models.Model):
    """Per-database storage of configuration key-value pairs."""

    _name = 'ir.config_parameter'
    _rec_name = 'key'

    key = fields.Char(required=True, index=True)
    value = fields.Text(required=True)
    group_ids = fields.Many2many('res.groups', 'ir_config_parameter_groups_rel', 'icp_id', 'group_id', string='Groups')

    _sql_constraints = [
        ('key_uniq', 'unique (key)', 'Key must be unique.')
    ]

    def init(self, force=False):
        """
        Initializes the parameters listed in _default_parameters.
        It overrides existing parameters if force is ``True``.
        """
        for key, func in _default_parameters.iteritems():
            # force=True skips search and always performs the 'if' body (because ids=False)
            self = not force and self.sudo().search([('key', '=', key)])
            if not self.ids:
                value, groups = func()
                self.sudo().set_param(key, value, groups=groups)

    @api.model
    def get_param(self, key, default=False):
        """Retrieve the value for a given key.

        :param string key: The key of the parameter value to retrieve.
        :param string default: default value if parameter is missing.
        :return: The value of the parameter, or ``default`` if it does not exist.
        :rtype: string
        """
        result = self._get_param(key)
        if result:
            return result
        return default

    @ormcache('uid', 'key')
    def _get_param(self, cr, uid, key):
        params = self.search_read(cr, uid, [('key', '=', key)], fields=['value'], limit=1)
        if not params:
            return None
        return params[0]['value']

    @api.model
    def set_param(self, key, value, groups=()):
        """Sets the value of a parameter.

        :param string key: The key of the parameter value to set.
        :param string value: The value to set.
        :param list of string groups: List of group (xml_id allowed) to read this key.
        :return: the previous value of the parameter or False if it did
                 not exist.
        :rtype: string
        """
        self._get_param.clear_cache(self)
        self = self.search([('key', '=', key)])

        gids = []
        for group_xml in groups:
            res_id = self.env['ir.model.data'].xmlid_to_res_id(group_xml)
            if res_id:
                gids.append((4, res_id))

        vals = {'value': value}
        if gids:
            vals.update(group_ids=gids)
        if self.ids:
            if value is not False and value is not None:
                self.write(vals)
            else:
                self.unlink()
            return self.value
        else:
            vals.update(key=key)
            if value is not False and value is not None:
                self.create(vals)
            return False

    @api.multi
    def write(self, vals):
        self._get_param.clear_cache(self)
        return super(IrConfigParameter, self).write(vals)

    @api.multi
    def unlink(self):
        self._get_param.clear_cache(self)
        return super(IrConfigParameter, self).unlink()
