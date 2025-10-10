# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""
Store database-specific configuration parameters
"""

import uuid
import logging
from typing import Literal, TypeVar

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import config, ormcache, mute_logger, str2bool

_logger = logging.getLogger(__name__)

T = TypeVar('T')

"""
A dictionary holding some configuration parameters to be initialized when the database is created.
"""
_default_parameters = {
    "database.secret": lambda: str(uuid.uuid4()),
    "database.uuid": lambda: str(uuid.uuid1()),
    "database.create_date": fields.Datetime.now,
    "web.base.url": lambda: "http://localhost:%s" % config.get('http_port'),
    "base.login_cooldown_after": lambda: 10,
    "base.login_cooldown_duration": lambda: 60,
}


class IrConfig_Parameter(models.Model):
    """Per-database storage of configuration key-value pairs."""
    _name = 'ir.config_parameter'
    _description = 'System Parameter'
    _rec_name = 'key'
    _order = 'key'
    _allow_sudo_commands = False

    key = fields.Char(required=True)
    value = fields.Text()

    _key_uniq = models.Constraint(
        'unique (key)',
        "Key must be unique.",
    )

    @mute_logger('odoo.addons.base.models.ir_config_parameter')
    def init(self, force=False):
        """
        Initializes the parameters listed in _default_parameters.
        It overrides existing parameters if force is ``True``.
        """
        # avoid prefetching during module installation, as the res_users table
        # may not have all prescribed columns
        self = self.with_context(prefetch_fields=False)
        for key, func in _default_parameters.items():
            # force=True skips search and always performs the 'if' body (because ids=False)
            params = self.sudo().search([('key', '=', key)])
            if force or not params:
                params.set_str(key, str(func()))  # use set_str as a hack for all types

    @api.model
    def set_bool(self, key, value):
        return self._set(key, str2bool(value or False), 'bool')

    @api.model
    def set_int(self, key, value):
        return self._set(key, None if value is None else int(value or 0), 'int')

    @api.model
    def set_float(self, key, value):
        return self._set(key, None if value is None else float(value or 0.0), 'float')

    @api.model
    def set_str(self, key, value):
        return self._set(key, None if value is None else str(value or ''), 'str')

    def _set(self, key: str, value: bool | float | str | None, type_: Literal['bool', 'int', 'float', 'str']):
        old_value, exists = self._get(key, type_)
        value_ = False if value is None else str(value)
        if not exists:
            self.create({'key': key, 'value': value_})
        elif old_value != value:
            param = self.search([('key', '=', key)])
            param.write({'value': value_})
        if old_value is not None:
            return old_value
        if type_ == 'bool':
            return False
        if type_ in ['int', 'float']:
            return 0
        return ''

    @api.model
    def get_bool(self, key: str, default: T = False) -> bool | T:
        self.browse().check_access('read')
        value = self._get(key, 'bool')[0]
        if value is None:
            return default
        return value

    @api.model
    def get_int(self, key: str, default: T = 0) -> int | T:
        self.browse().check_access('read')
        value = self._get(key, 'int')[0]
        if value is None:
            return default
        return value

    @api.model
    def get_float(self, key: str, default: T = 0.0) -> float | T:
        self.browse().check_access('read')
        value = self._get(key, 'float')[0]
        if value is None:
            return default
        return value

    @api.model
    def get_str(self, key: str, default: T = '') -> str | T:
        self.browse().check_access('read')
        value = self._get(key, 'str')[0]
        if value is None:
            return default
        return value

    @ormcache('key', 'type_', cache='stable')
    def _get(self, key, type_='str'):
        """
        Returns the value of the config parameter and whether the record exists.
        """
        self.flush_model(['key', 'value'])
        self.env.cr.execute("SELECT value FROM ir_config_parameter WHERE key = %s", [key])
        result = self.env.cr.fetchone()
        if not result:
            return None, False
        value = result[0]
        if value is None:
            # ir_config_parameter.write({'value': False}) from UI can logically set the config to undefined
            return None, True
        try:
            return self._convert_type(value, type_), True
        except ValueError:
            _logger.error("ir.config_parameter with key %s has invalid value %s for type %s", key, value, type_)
            return None, True

    def _convert_type(self, value: str, type_: Literal['bool', 'int', 'float', 'str']) -> bool | float | str:
        if type_ == 'bool':
            return str2bool(value)
        if type_ == 'int':
            return int(value)
        if type_ == 'float':
            return float(value)
        if type_ == 'str':
            return value
        raise ValueError("Invalid type: %s" % type_)

    @api.model
    def get_param(self, key, default=False):
        return self._get(key, 'str')[0] or default

    @api.model
    def set_param(self, key, value):
        if value is not False and value is not None:
            value = str(value)
        else:
            value = None
        self._set(key, value, 'str')

    @api.model_create_multi
    def create(self, vals_list):
        self.env.registry.clear_cache('stable')
        return super().create(vals_list)

    def write(self, vals):
        if 'key' in vals:
            illegal = _default_parameters.keys() & self.mapped('key')
            if illegal:
                raise ValidationError(self.env._("You cannot rename config parameters with keys %s", ', '.join(illegal)))
        self.env.registry.clear_cache('stable')
        return super().write(vals)

    def unlink(self):
        self.env.registry.clear_cache('stable')
        return super().unlink()

    @api.ondelete(at_uninstall=False)
    def unlink_default_parameters(self):
        for record in self.filtered(lambda p: p.key in _default_parameters.keys()):
            raise ValidationError(self.env._("You cannot delete the %s record.", record.key))
