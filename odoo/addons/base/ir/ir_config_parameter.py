# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""
Store database-specific configuration parameters
"""

import uuid
import logging

from odoo import api, fields, models
from odoo.tools import config, ormcache, mute_logger, pycompat

_logger = logging.getLogger(__name__)

"""
A dictionary holding some configuration parameters to be initialized when the database is created.
"""
_default_parameters = {
    "database.secret": lambda: str(uuid.uuid4()),
    "database.uuid": lambda: str(uuid.uuid1()),
    "database.create_date": fields.Datetime.now,
    "web.base.url": lambda: "http://localhost:%s" % config.get('xmlrpc_port'),
}


class IrConfigParameter(models.Model):
    """Per-database storage of configuration key-value pairs."""
    _name = 'ir.config_parameter'
    _rec_name = 'key'

    key = fields.Char(required=True, index=True)
    value = fields.Text(required=True)

    _sql_constraints = [
        ('key_uniq', 'unique (key)', 'Key must be unique.')
    ]

    @api.model_cr
    @mute_logger('odoo.addons.base.ir.ir_config_parameter')
    def init(self, force=False):
        """
        Initializes the parameters listed in _default_parameters.
        It overrides existing parameters if force is ``True``.
        """
        for key, func in pycompat.items(_default_parameters):
            # force=True skips search and always performs the 'if' body (because ids=False)
            params = self.sudo().search([('key', '=', key)])
            if force or not params:
                params.set_param(key, func())

    @api.model
    def get_param(self, key, default=False):
        """Retrieve the value for a given key.

        :param string key: The key of the parameter value to retrieve.
        :param string default: default value if parameter is missing.
        :return: The value of the parameter, or ``default`` if it does not exist.
        :rtype: string
        """
        return self._get_param(key) or default

    @api.model
    @ormcache('self._uid', 'key')
    def _get_param(self, key):
        params = self.search_read([('key', '=', key)], fields=['value'], limit=1)
        return params[0]['value'] if params else None

    @api.model
    def set_param(self, key, value):
        """Sets the value of a parameter.

        :param string key: The key of the parameter value to set.
        :param string value: The value to set.
        :return: the previous value of the parameter or False if it did
                 not exist.
        :rtype: string
        """
        param = self.search([('key', '=', key)])
        if param:
            old = param.value
            if value is not False and value is not None:
                param.write({'value': value})
            else:
                param.unlink()
            return old
        else:
            if value is not False and value is not None:
                self.create({'key': key, 'value': value})
            return False

    @api.model
    def create(self, vals):
        self.clear_caches()
        return super(IrConfigParameter, self).create(vals)

    @api.multi
    def write(self, vals):
        self.clear_caches()
        return super(IrConfigParameter, self).write(vals)

    @api.multi
    def unlink(self):
        self.clear_caches()
        return super(IrConfigParameter, self).unlink()
