import json
from typing import Any

from odoo import api, fields, models
from odoo.exceptions import AccessError, ConcurrencyError, LockError, ValidationError


class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    embedded_actions_config_ids = fields.One2many(
        comodel_name="res.users.settings.embedded.action",
        inverse_name="user_setting_id",
    )
    density = fields.Selection(
        selection=[
            ("default", "Default"),
            ("compact", "Compact"),
            ("condensed", "Condensed"),
        ],
        string="Content Density",
        default="default",
        required=True,
    )
    color_scheme = fields.Selection(
        selection=[
            ("system", "System"),
            ("light", "Light"),
            ("dark", "Dark"),
        ],
        default="system",
        required=True,
    )
    homemenu_config = fields.Json(
        string="Home Menu Configuration",
        readonly=True,
    )
    homemenu_usage = fields.Json(
        string="Home Menu Usage",
        readonly=True,
        help="Which menus this user opens and when, as the app launcher's "
        "recents rank them. Held here rather than in the browser so a second "
        "device does not start blank.",
    )

    @api.model
    def _normalize_homemenu_config(self, value: Any) -> dict[str, Any] | None:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                return None
        if isinstance(value, list):
            value = {"order": value}
        if not isinstance(value, dict) or value.get("version", 2) != 2:
            return None
        result: dict[str, Any] = {"version": 2}
        for key in ("order", "pinned", "hidden"):
            items = value.get(key, [])
            result[key] = (
                list(
                    dict.fromkeys(
                        item for item in items if isinstance(item, str) and item
                    )
                )
                if isinstance(items, list)
                else []
            )
        result["pinned"] = [
            item for item in result["pinned"] if item not in result["hidden"]
        ]
        return result

    def update_homemenu_config(self, changes: list[dict[str, Any]]) -> dict[str, Any]:
        self.check_singleton()
        self.check_access("write")
        if self.user_id != self.env.user:
            raise AccessError(self.env._("You can only customize your own launcher."))
        if not isinstance(changes, list) or len(changes) > 500:
            raise ValidationError(self.env._("Invalid launcher changes."))
        try:
            self.lock_for_update()
        except LockError as error:
            raise ConcurrencyError("Concurrent launcher customization") from error
        self.invalidate_recordset(["homemenu_config"])
        config = self._normalize_homemenu_config(self.homemenu_config)
        for change in changes:
            if not isinstance(change, dict):
                raise ValidationError(self.env._("Invalid launcher change."))
            operation = change.get("operation")
            if operation == "reset":
                config = None
                continue
            if config is None:
                config = self._normalize_homemenu_config(
                    self.env.company.homemenu_default_config
                ) or {"version": 2, "order": [], "pinned": [], "hidden": []}
            if operation in ("order", "pinned_order"):
                key = "order" if operation == "order" else "pinned"
                values = change.get("value")
                if not isinstance(values, list) or any(
                    not isinstance(v, str) or not v for v in values
                ):
                    raise ValidationError(self.env._("Invalid launcher order."))
                requested = list(dict.fromkeys(values))
                if key == "pinned":
                    requested = [item for item in requested if item in config[key]]
                config[key] = requested + [
                    item for item in config[key] if item not in requested
                ]
            elif operation in ("pin", "hide"):
                xmlid, enabled = change.get("xmlid"), change.get("value")
                if (
                    not isinstance(xmlid, str)
                    or not xmlid
                    or not isinstance(enabled, bool)
                ):
                    raise ValidationError(self.env._("Invalid launcher app."))
                key = "pinned" if operation == "pin" else "hidden"
                if not enabled:
                    config[key] = [item for item in config[key] if item != xmlid]
                if enabled:
                    if xmlid not in config[key]:
                        config[key].append(xmlid)
                    other = "hidden" if key == "pinned" else "pinned"
                    config[other] = [item for item in config[other] if item != xmlid]
            else:
                raise ValidationError(self.env._("Unknown launcher change."))
        self.homemenu_config = config
        return self._res_users_settings_format(["homemenu_config", "id"])

    @api.model
    def _format_settings(self, fields_to_format: list[str]) -> dict[str, Any]:
        res = super()._format_settings(fields_to_format)
        if "embedded_actions_config_ids" in fields_to_format:
            res["embedded_actions_config_ids"] = (
                self.embedded_actions_config_ids._format_embedded_action_settings()
            )
        return res

    def get_embedded_actions_settings(self) -> dict[str, Any]:
        self.check_singleton()
        return self.embedded_actions_config_ids._format_embedded_action_settings()

    def set_embedded_actions_setting(
        self, action_id: int, res_id: int, vals: dict[str, Any]
    ) -> None:
        self.check_singleton()
        embedded_actions_config = self.env["res.users.settings.embedded.action"].search(
            [
                ("user_setting_id", "=", self.id),
                ("action_id", "=", action_id),
                ("res_id", "=", res_id),
            ],
            limit=1,
        )
        _ID_LIST_FIELDS = ("embedded_actions_order", "embedded_actions_visibility")
        _SETTABLE_FIELDS = (*_ID_LIST_FIELDS, "embedded_visibility", "res_model")
        new_vals = {}
        for field, value in vals.items():
            if field not in _SETTABLE_FIELDS:
                continue
            if field in _ID_LIST_FIELDS:
                new_vals[field] = ",".join(
                    "false" if act_id is False else str(act_id) for act_id in value
                )
            else:
                new_vals[field] = value
        if embedded_actions_config:
            embedded_actions_config.write(new_vals)
        else:
            self.env["res.users.settings.embedded.action"].create(
                {
                    **new_vals,
                    "user_setting_id": self.id,
                    "action_id": action_id,
                    "res_id": res_id,
                }
            )
