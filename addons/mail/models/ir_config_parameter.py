import logging
from collections import defaultdict
from typing import Any, Literal, Self

from odoo import api, models
from odoo.api import ValuesType
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

RESTRICT_TEMPLATE_RENDERING_KEY = "mail.restrict.template.rendering"


class IrConfig_Parameter(models.Model):
    _inherit = "ir.config_parameter"

    @api.model
    def _get_int_param(self, key: str, default: int) -> int:
        return self.sudo().get_param_int(key, default)

    @api.model
    def _get_positive_int_param(self, key: str, default: int) -> int:
        value = self._get_int_param(key, default)
        if value < 1:
            if value != 0:
                _logger.warning(
                    "Ignoring %s = %s: a count below one has no meaning here, "
                    "falling back to %s",
                    key,
                    value,
                    default,
                )
            return default
        return value

    @api.model
    def _get_bool_param(self, key: str, default: bool = False) -> bool:
        return self.sudo().get_param_bool(key, default)

    @api.model
    def _sync_template_editor_group(self, restrict: bool) -> None:
        group_user = self.env.ref("base.group_user")
        group_mail_template_editor = self.env.ref("mail.group_mail_template_editor")
        if not restrict and group_mail_template_editor not in group_user.implied_ids:
            _debug.lifecycle("template_editor_group", restrict=False, action="implied")
            group_user._add_implied_group(group_mail_template_editor)
        elif restrict and group_mail_template_editor in group_user.implied_ids:
            _debug.lifecycle("template_editor_group", restrict=True, action="removed")
            group_user._remove_group(group_mail_template_editor)

    @api.model
    def _restricts_template_rendering(self, value: Any) -> bool:
        if value is False or value is None:
            return False
        return str(value).strip().lower() not in self._FALSY_PARAM_VALUES

    @api.model
    def set_param(self, key: str, value: Any) -> Literal[True]:
        if key == RESTRICT_TEMPLATE_RENDERING_KEY:
            self._sync_template_editor_group(self._restricts_template_rendering(value))
        elif key == "mail.catchall.domain.allowed":
            value = (
                self.env["mail.alias.domain"]._normalize_allowed_domains(value)
                if value
                else False
            )
            _debug.logic("allowed_domains_sanitized", value=value)

        return super().set_param(key, value)

    def _normalize_param_value(self, key: str, value: Any) -> str:
        if key == "mail.catchall.domain.allowed" and value:
            return self.env["mail.alias.domain"]._normalize_allowed_domains(value)
        return value

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        for vals in vals_list:
            if vals.get("key") and "value" in vals:
                vals["value"] = self._normalize_param_value(vals["key"], vals["value"])
        params = super().create(vals_list)
        params._sync_template_editor_group_from_rows()
        return params

    def write(self, vals: ValuesType) -> Literal[True]:
        watched = "key" in vals or "value" in vals
        had_restrict_row = watched and self._has_restrict_template_rendering_row()
        if "value" in vals:
            records_by_value = defaultdict(self.browse)
            for record in self:
                key = vals.get("key", record.key)
                records_by_value[self._normalize_param_value(key, vals["value"])] |= (
                    record
                )
            result = True
            for value, records in records_by_value.items():
                result = (
                    super(IrConfig_Parameter, records).write({**vals, "value": value})
                    and result
                )
        else:
            result = super().write(vals)
        if watched:
            self._sync_template_editor_group_from_rows(
                row_removed=had_restrict_row
                and not self._has_restrict_template_rendering_row()
            )
        return result

    def unlink(self) -> Literal[True]:
        had_restrict_row = self._has_restrict_template_rendering_row()
        result = super().unlink()
        if had_restrict_row:
            self._sync_template_editor_group(False)
        return result

    def _has_restrict_template_rendering_row(self) -> bool:
        return any(p.key == RESTRICT_TEMPLATE_RENDERING_KEY for p in self)

    def _sync_template_editor_group_from_rows(self, row_removed: bool = False) -> None:
        rows = self.filtered(lambda p: p.key == RESTRICT_TEMPLATE_RENDERING_KEY)
        if rows:
            self._sync_template_editor_group(
                self._restricts_template_rendering(rows[-1].value)
            )
        elif row_removed:
            self._sync_template_editor_group(False)
