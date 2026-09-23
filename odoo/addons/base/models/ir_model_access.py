import logging
from typing import Any, Self

from odoo import _, api, fields, models, tools
from odoo.api import ValuesType
from odoo.exceptions import AccessError, UserError
from odoo.libs.debug_log import DebugLog

from .ir_model_common import check_access_mode, unloaded_module_scope

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class IrModelAccess(models.Model):
    _name = "ir.model.access"
    _description = "Model Access"
    _order = "model_id,group_id,name,id"
    _allow_sudo_commands = False

    name = fields.Char(
        index=True,
        required=True,
    )
    active = fields.Boolean(
        default=True,
        help="If you uncheck the active field, it will disable the ACL without deleting it (if you delete a native ACL, it will be re-created when you reload the module).",
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        index=True,
        required=True,
        ondelete="cascade",
    )
    group_id = fields.Many2one(
        comodel_name="res.groups",
        index=True,
        ondelete="restrict",
    )
    perm_read = fields.Boolean(string="Read Access")
    perm_write = fields.Boolean(string="Write Access")
    perm_create = fields.Boolean(string="Create Access")
    perm_unlink = fields.Boolean(string="Delete Access")

    _check_access_mode = staticmethod(check_access_mode)

    @api.model
    def group_names_with_access(self, model_name: str, access_mode: str) -> list[str]:
        self._check_access_mode(access_mode)
        return self.env["ir.access"]._group_names_with_access(model_name, access_mode)

    @api.model
    @tools.ormcache("model_name", "access_mode", cache="stable")
    def _get_groups_with_access(
        self, model_name: str, access_mode: str = "read"
    ) -> Any:
        letter = self.env["ir.access"]._operation_letter(access_mode)
        group_ids = {
            row.group_id
            for row in self.env["ir.access"]._get_all_access().get(model_name, ())
            if row.kind == "permission" and letter in row.operation
        }
        group_definitions = self.env["res.groups"]._get_group_definitions()
        if not group_ids:
            _debug.logic(
                "groups_with_access", model=model_name, mode=access_mode, result="empty"
            )
            return group_definitions.empty
        _debug.logic(
            "groups_with_access",
            model=model_name,
            mode=access_mode,
            result="groups",
            groups=len(group_ids),
        )
        return group_definitions.from_ids(sorted(group_ids))

    @tools.ormcache(
        "self.env.user._get_group_ids()", "mode", "self._get_unloaded_module_scope()"
    )
    def _get_models_allowed(self, mode: str = "read") -> frozenset[str]:
        self._check_access_mode(mode)
        letter = self.env["ir.access"]._operation_letter(mode)
        group_ids = set(self.env.user._get_group_ids())
        models_allowed = frozenset(
            model_name
            for model_name, rows in self.env["ir.access"]._get_all_access().items()
            if any(
                row.kind == "permission"
                and letter in row.operation
                and row.group_id in group_ids
                for row in rows
            )
        )
        _debug.perf.count(
            "models_allowed_computed",
            mode=mode,
            uid=self.env.uid,
            groups=len(group_ids),
            models=len(models_allowed),
        )
        return models_allowed

    def _get_unloaded_module_scope(self) -> tuple[int, str | None] | None:
        return unloaded_module_scope(self.env)

    @api.model
    def check(
        self, model: str, mode: str = "read", raise_exception: bool = True
    ) -> bool:
        if self.env.su:
            return True

        if not isinstance(model, str):
            _debug.logic("acl_check.rejected", mode=mode, reason="model_not_str")
            raise TypeError(
                f"Model name must be a string, got {type(model).__name__}: {model!r}"
            )

        if model not in self.env:
            _debug.logic(
                "acl_check.unknown_model",
                model=model,
                mode=mode,
                raise_exception=raise_exception,
            )
            if raise_exception:
                raise ValueError(
                    f"Unknown model {model!r}: it does not exist in the registry"
                    " (check for a typo or a missing/uninstalled module)."
                )
            _logger.warning("Missing model %s", model)
            return False

        self._check_access_mode(mode)
        has_access = self.env[model]._access_allowed(mode)
        if _debug.logic.enabled and not has_access:
            _debug.logic(
                "acl_denied",
                model=model,
                mode=mode,
                uid=self.env.uid,
                raise_exception=raise_exception,
            )
        if not has_access and raise_exception:
            raise self._prepare_access_error(model, mode) from None
        return has_access

    def _prepare_access_error(self, model: str, mode: str) -> AccessError:
        return self.env["ir.access"]._make_model_access_error(model, mode)

    @api.model
    def call_cache_clearing_methods(self) -> None:
        _debug.lifecycle("acl_cache_cleared")
        self.env.invalidate_all()
        self.env.registry.clear_cache("stable")

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        if not vals_list:
            return self.browse()
        raise UserError(
            _(
                "Access lines are ir.access rows now: create a permission row of "
                "ir.access (a module ships it in security/ir.access.csv) instead of "
                "an ir.model.access line."
            )
        )

    def write(self, vals: dict[str, Any]) -> bool:
        _debug.lifecycle("write", count=len(self), fields=list(vals))
        res = super().write(vals)
        self.call_cache_clearing_methods()
        return res

    def unlink(self) -> bool:
        _debug.lifecycle("unlink", count=len(self))
        res = super().unlink()
        self.call_cache_clearing_methods()
        return res
