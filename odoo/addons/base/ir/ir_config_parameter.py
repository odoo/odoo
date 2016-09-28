# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""
Store database-specific configuration parameters
"""

import uuid
import logging

from odoo import api, fields, models
from odoo.tools import config, ormcache, mute_logger

_logger = logging.getLogger(__name__)

"""
A dictionary holding some configuration parameters to be initialized when the database is created.
"""
_default_parameters = {
    "database.secret": lambda: (str(uuid.uuid4()), ['base.group_erp_manager']),
    "database.uuid": lambda: (str(uuid.uuid1()), []),
    "database.create_date": lambda: (fields.Datetime.now(), ['base.group_user']),
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

    @api.model_cr
    @mute_logger('odoo.addons.base.ir.ir_config_parameter')
    def init(self, force=False):
        """
        Initializes the parameters listed in _default_parameters.
        It overrides existing parameters if force is ``True``.
        """
        for key, func in _default_parameters.iteritems():
            # force=True skips search and always performs the 'if' body (because ids=False)
            params = self.sudo().search([('key', '=', key)])
            if force or not params:
                value, groups = func()
                params.set_param(key, value, groups=groups)

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
        param = self.search([('key', '=', key)])

        gids = []
        for group_xml in groups:
            group = self.env.ref(group_xml, raise_if_not_found=False)
            if group:
                gids.append((4, group.id))
            else:
                _logger.warning('Potential Security Issue: Group [%s] is not found.' % group_xml)

        vals = {'value': value}
        if gids:
            vals.update(group_ids=gids)
        if param:
            old = param.value
            if value is not False and value is not None:
                param.write(vals)
            else:
                param.unlink()
            return old
        else:
            vals.update(key=key)
            if value is not False and value is not None:
                self.create(vals)
            return False

    @api.multi
    def write(self, vals):
        self.clear_caches()
        return super(IrConfigParameter, self).write(vals)

    @api.multi
    def unlink(self):
        self.clear_caches()
        return super(IrConfigParameter, self).unlink()
