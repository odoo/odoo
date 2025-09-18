"""
Store database-specific configuration parameters
"""

import logging
import uuid
from typing import Any, Self

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import config, mute_logger, ormcache
from odoo.orm._typing import ValuesType

_logger = logging.getLogger(__name__)

"""
A dictionary holding some configuration parameters to be initialized when the database is created.
"""
_default_parameters = {
    "database.secret": lambda: str(uuid.uuid4()),
    "database.uuid": lambda: str(uuid.uuid4()),
    "database.create_date": fields.Datetime.now,
    "web.base.url": lambda: f"http://localhost:{config.get('http_port')}",
    "base.login_cooldown_after": lambda: 10,
    "base.login_cooldown_duration": lambda: 60,
}


class IrConfig_Parameter(models.Model):
    """Per-database storage of configuration key-value pairs."""

    _name = "ir.config_parameter"
    _description = "System Parameter"
    _rec_name = "key"
    _order = "key"
    _allow_sudo_commands = False

    key = fields.Char(required=True)
    value = fields.Text(required=True)

    _key_uniq = models.Constraint(
        "unique (key)",
        "Key must be unique.",
    )

    @mute_logger("odoo.addons.base.models.ir_config_parameter")
    def init(self, force: bool = False) -> None:
        """
        Initializes the parameters listed in _default_parameters.
        It overrides existing parameters if force is ``True``.
        """
        # avoid prefetching during module installation, as the res_users table
        # may not have all prescribed columns
        self = self.with_context(prefetch_fields=False)
        for key, func in _default_parameters.items():
            # force=True skips search and always performs the 'if' body (because ids=False)
            params = self.sudo().search([("key", "=", key)])
            if force or not params:
                params.set_param(key, func())

    @api.model
    def get_param(self, key: str, default: str | bool = False) -> str | bool:
        """Retrieve the value for a given key.

        :param str key: The key of the parameter value to retrieve.
        :param str | bool default: default value if parameter is missing.
        :return: The value of the parameter, or ``default`` if it does not exist.
        :rtype: str | bool
        """
        self.browse().check_access("read")
        value = self._get_param(key)
        return default if value is None else value

    @api.model
    @ormcache("key", cache="stable")
    def _get_param(self, key: str) -> str | None:
        # we bypass the ORM because get_param() is used in some field's depends,
        # and must therefore work even when the ORM is not ready to work
        self.flush_model(["key", "value"])
        self.env.cr.execute(
            "SELECT value FROM ir_config_parameter WHERE key = %s", [key]
        )
        result = self.env.cr.fetchone()
        return result and result[0]

    @api.model
    def set_param(self, key: str, value: Any) -> str | bool:
        """Sets the value of a parameter.

        :param str key: The key of the parameter value to set.
        :param Any value: The value to set.
        :return: the previous value of the parameter or False if it did
                 not exist.
        :rtype: str | bool
        """
        param = self.search([("key", "=", key)])
        if param:
            old = param.value
            if value is not False and value is not None:
                if str(value) != old:
                    param.write({"value": value})
            else:
                param.unlink()
            return old
        else:
            if value is not False and value is not None:
                self.create({"key": key, "value": value})
            return False

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        self.env.registry.clear_cache("stable")
        return super().create(vals_list)

    def write(self, vals: dict[str, Any]) -> bool:
        if "key" in vals:
            illegal = _default_parameters.keys() & self.mapped("key")
            if illegal:
                raise ValidationError(
                    self.env._(
                        "You cannot rename config parameters with keys %s",
                        ", ".join(illegal),
                    )
                )
        self.env.registry.clear_cache("stable")
        return super().write(vals)

    def unlink(self) -> bool:
        self.env.registry.clear_cache("stable")
        return super().unlink()

    @api.ondelete(at_uninstall=False)
    def unlink_default_parameters(self) -> None:
        for record in self.filtered(lambda p: p.key in _default_parameters):
            raise ValidationError(
                self.env._("You cannot delete the %s record.", record.key)
            )
