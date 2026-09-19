import logging
from typing import Any, Self

from odoo import api, fields, models, tools
from odoo.api import ValuesType
from odoo.exceptions import AccessError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

from .ir_model_common import (
    ACCESS_ERROR_GROUPS,
    ACCESS_ERROR_HEADER,
    ACCESS_ERROR_NOGROUP,
    ACCESS_ERROR_RESOLUTION,
    access_mode_columns,
    check_access_mode,
    unloaded_module_clause,
    unloaded_module_scope,
)

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class IrModelAccess(models.Model):
    _name = "ir.model.access"
    _description = "Model Access"
    _order = "model_id,group_id,name,id"
    _allow_sudo_commands = False
    _PERM_COLUMNS = access_mode_columns("a")

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
        rows = self.sudo()._read_group(
            [
                ("model_id.model", "=", model_name),
                (f"perm_{access_mode}", "=", True),
                ("group_id", "!=", False),
            ],
            ["group_id", "group_id.privilege_id.name", "group_id.name"],
            [],
        )
        names = sorted(
            ((privilege or None, group) for _group, privilege, group in rows),
            key=lambda pair: (pair[0] is None, pair[0] or "", pair[1]),
        )
        _debug.perf.count(
            "group_names_with_access",
            model=model_name,
            mode=access_mode,
            groups=len(names),
        )
        return [
            f"{privilege}/{group}" if privilege else group for privilege, group in names
        ]

    @api.model
    @tools.ormcache("model_name", "access_mode", cache="stable")
    def _get_groups_with_access(
        self, model_name: str, access_mode: str = "read"
    ) -> Any:
        self._check_access_mode(access_mode)
        model = self.env["ir.model"]._get(model_name)
        accesses = self.sudo().search(
            [
                (f"perm_{access_mode}", "=", True),
                ("model_id", "=", model.id),
            ]
        )

        group_definitions = self.env["res.groups"]._get_group_definitions()
        if not accesses:
            _debug.logic(
                "groups_with_access", model=model_name, mode=access_mode, result="empty"
            )
            return group_definitions.empty
        if not all(access.group_id for access in accesses):
            _debug.logic(
                "groups_with_access",
                model=model_name,
                mode=access_mode,
                result="universe",
            )
            return group_definitions.universe
        _debug.logic(
            "groups_with_access",
            model=model_name,
            mode=access_mode,
            result="groups",
            groups=len(accesses.group_id),
        )
        return group_definitions.from_ids(accesses.group_id.ids)

    @tools.ormcache(
        "self.env.user._get_group_ids()", "mode", "self._get_unloaded_module_scope()"
    )
    def _get_models_allowed(self, mode: str = "read") -> frozenset[str]:
        self._check_access_mode(mode)

        group_ids = self.env.user._get_group_ids()
        self.flush_model()
        rows = self.env.execute_query(
            SQL(
                """
            SELECT m.model
              FROM ir_model_access a
              JOIN ir_model m ON (m.id = a.model_id)
             WHERE %s
               AND a.active
               AND (
                    a.group_id IS NULL OR
                    a.group_id = ANY(%s)
                )
               %s
            GROUP BY m.model
        """,
                self._PERM_COLUMNS[mode],
                list(group_ids),
                unloaded_module_clause(self.env, "ir.model.access", "a"),
            )
        )

        _debug.perf.count(
            "models_allowed_computed",
            mode=mode,
            uid=self.env.uid,
            groups=len(group_ids),
            models=len(rows),
        )
        return frozenset(v[0] for v in rows)

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

        allowed = self._get_models_allowed(mode)
        has_access = any(
            name in allowed
            for name in self.env["ir.rule"]._get_model_names_bound_by_rules(model)
        )
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
        _logger.info(
            "Access Denied by ACLs for operation: %s, uid: %s, model: %s",
            mode,
            self.env.uid,
            model,
        )

        operation_error = str(ACCESS_ERROR_HEADER[mode]) % {
            "document_kind": self.env["ir.model"]._get(model).name or model,
            "document_model": model,
        }

        groups = "\n".join(
            f"\t- {g}" for g in self.group_names_with_access(model, mode)
        )
        if groups:
            group_info = str(ACCESS_ERROR_GROUPS) % {"groups_list": groups}
        else:
            _debug.logic("access_error.no_group_grants", model=model, mode=mode)
            group_info = str(ACCESS_ERROR_NOGROUP)

        resolution_info = str(ACCESS_ERROR_RESOLUTION)

        return AccessError(
            operation_error + "\n\n" + group_info + "\n\n" + resolution_info
        )

    @api.model
    def call_cache_clearing_methods(self) -> None:
        _debug.lifecycle("acl_cache_cleared")
        self.env.invalidate_all()
        self.env.registry.clear_cache("stable")

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        for vals in vals_list:
            if not vals.get("group_id") and any(
                vals.get(f"perm_{mode}") for mode in self._PERM_COLUMNS
            ):
                _debug.logic("create.groupless_acl", name=vals.get("name"))
                _logger.warning(
                    "Rule %s has no group, this is a deprecated feature. Every access-granting rule should specify a group.",
                    vals.get("name"),
                )
        records = super().create(vals_list)
        _debug.lifecycle("create", count=len(records))
        self.call_cache_clearing_methods()
        return records

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
