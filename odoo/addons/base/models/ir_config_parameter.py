import logging
import uuid
from typing import Any, Self

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.db import get_or_create_row
from odoo.exceptions import ValidationError
from odoo.libs import sealing
from odoo.libs.debug_log import DebugLog
from odoo.tools import config, mute_logger, ormcache

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


_default_parameters = {
    "database.secret": lambda: str(uuid.uuid4()),
    "database.uuid": lambda: str(uuid.uuid4()),
    "database.create_date": fields.Datetime.now,
    "web.base.url": lambda: f"http://localhost:{config.get('http_port')}",
    "base.login_cooldown_after": lambda: 10,
    "base.login_cooldown_duration": lambda: 60,
}

_SEALED_PARAMETERS = frozenset({"database.secret"})


class IrConfig_Parameter(models.Model):
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
        self = self.with_context(prefetch_fields=False).sudo()
        present = set(
            self.search([("key", "in", list(_default_parameters))]).mapped("key")
        )
        _debug.pipeline(
            "init_defaults",
            declared=len(_default_parameters),
            present=len(present),
            force=force,
        )
        for key, func in _default_parameters.items():
            if force or key not in present:
                _debug.lifecycle("default_param_set", key=key, force=force)
                self.set_param(key, func())

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        _debug.lifecycle("create", keys=[vals.get("key") for vals in vals_list])
        self.env.registry.clear_cache("stable")
        return super().create(
            [
                {**vals, "value": self._seal_value(vals["key"], vals["value"])}
                if vals.get("key") in _SEALED_PARAMETERS and "value" in vals
                else vals
                for vals in vals_list
            ]
        )

    def write(self, vals: dict[str, Any]) -> bool:
        if "key" in vals:
            illegal = _default_parameters.keys() & self.mapped("key")
            if illegal:
                _debug.logic("rename_refused", keys=sorted(illegal))
                raise ValidationError(
                    self.env._(
                        "You cannot rename config parameters with keys %s",
                        ", ".join(illegal),
                    )
                )
        _debug.lifecycle("write", keys=self.mapped("key"), fields=list(vals))
        self.env.registry.clear_cache("stable")
        sealed = self.filtered(lambda param: param.key in _SEALED_PARAMETERS)
        if "value" in vals and sealed:
            _debug.logic(
                "write_sealed_split", sealed=len(sealed), clear=len(self - sealed)
            )
            super(IrConfig_Parameter, sealed).write(
                {**vals, "value": self._seal_value(sealed[:1].key, vals["value"])}
            )
            return super(IrConfig_Parameter, self - sealed).write(vals)
        return super().write(vals)

    def unlink(self) -> bool:
        _debug.lifecycle("unlink", keys=self.mapped("key"))
        self.env.registry.clear_cache("stable")
        return super().unlink()

    @api.ondelete(at_uninstall=False)
    def _unlink_except_default_parameter(self) -> None:
        for record in self.filtered(lambda p: p.key in _default_parameters):
            _debug.logic("unlink_refused", key=record.key, reason="default_parameter")
            raise ValidationError(
                self.env._("You cannot delete the %s record.", record.key)
            )

    @api.model
    def get_param(self, key: str, default: str | bool = False) -> str | bool:
        self.browse().check_access("read")
        value = self._get_param(key)
        if key in _SEALED_PARAMETERS and sealing.is_sealed(value):
            _debug.logic("param_unsealed", key=key)
            value = self._unseal_param(key, value)
        return default if value is None else value

    @api.model
    @ormcache("key", "sealed", cache="stable")
    def _unseal_param(self, key: str, sealed: str) -> str:
        try:
            return sealing.unseal(sealed)
        except sealing.SealError:
            _debug.logic("unseal_failed", key=key)
            _logger.critical(
                "The system parameter %s is sealed and cannot be opened: set the "
                "ODOO_API_ENCRYPTION_KEY it was sealed with",
                key,
            )
            raise

    @api.model
    def _seal_value(self, key: str, value: Any) -> Any:
        if not value or sealing.is_sealed(value) or not sealing.protects():
            return value
        _debug.logic("param_sealed", key=key)
        return sealing.seal(str(value))

    def _register_hook(self) -> None:
        super()._register_hook()
        self._seal_sealed_parameters()

    @api.model
    def _seal_sealed_parameters(self) -> None:
        params = self.sudo().search([("key", "in", list(_SEALED_PARAMETERS))])
        _debug.pipeline(
            "sealed_parameters_checked",
            params=len(params),
            configured=sealing.is_configured(),
            protects=sealing.protects(),
        )
        for param in params:
            if sealing.is_sealed(param.value):
                if not sealing.is_configured():
                    _logger.error(
                        "The system parameter %s is sealed but "
                        "ODOO_API_ENCRYPTION_KEY is not set: signed links, CSRF "
                        "tokens and sessions cannot be verified",
                        param.key,
                    )
            elif not sealing.is_configured():
                _logger.warning(
                    "The system parameter %s is stored in clear: set "
                    "ODOO_API_ENCRYPTION_KEY so every backup stops carrying it",
                    param.key,
                )
            elif sealing.protects() and not self.env.cr.readonly:
                _debug.lifecycle("param_sealed_on_hook", key=param.key)
                param.write({"value": param.value})

    @api.model
    def get_param_int(self, key: str, default: int) -> int:
        raw = self.get_param(key)
        if raw is False or raw is None or raw == "":
            return default
        try:
            return int(raw)
        except TypeError, ValueError:
            _logger.warning(
                "Invalid %s value: %r, falling back to %r", key, raw, default
            )
            _debug.logic("param_cast_fallback", key=key, cast="int")
            return default

    @api.model
    def get_param_float(self, key: str, default: float) -> float:
        raw = self.get_param(key)
        if raw is False or raw is None or raw == "":
            return default
        try:
            return float(raw)
        except TypeError, ValueError:
            _logger.warning(
                "Invalid %s value: %r, falling back to %r", key, raw, default
            )
            _debug.logic("param_cast_fallback", key=key, cast="float")
            return default

    _FALSY_PARAM_VALUES = frozenset({"", "0", "false", "no", "off", "none"})

    @api.model
    def get_param_bool(self, key: str, default: bool = False) -> bool:
        raw = self.get_param(key)
        if raw is False or raw is None:
            return default
        return str(raw).strip().lower() not in self._FALSY_PARAM_VALUES

    @api.model
    @ormcache("key", cache="stable")
    def _get_param(self, key: str) -> str | None:
        param = self.sudo().search_fetch([("key", "=", key)], ["value"], limit=1)
        _debug.perf.count("param_read", key=key, found=bool(param))
        return param.value if param else None

    @api.model
    def set_param(self, key: str, value: Any) -> str | bool:
        param = self.search([("key", "=", key)])
        if not param:
            if value is False or value is None:
                _debug.logic("set_param", key=key, action="noop_absent")
                return False
            param, created = get_or_create_row(
                self.env.cr,
                lambda: self.create({"key": key, "value": value}),
                lambda: self.search([("key", "=", key)]),
                conflict=f"ir.config_parameter {key!r}",
            )
            _debug.logic("set_param", key=key, action="create", created=created)
            if created:
                return False

        old = param.value
        if value is False or value is None:
            _debug.logic("set_param", key=key, action="unlink")
            param.unlink()
        elif str(value) != old:
            _debug.logic("set_param", key=key, action="write")
            param.write({"value": value})
        return old
