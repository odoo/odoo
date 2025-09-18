from typing import Any, Self

from odoo import api, fields, models


class ResUsersSettings(models.Model):
    _name = "res.users.settings"
    _description = "User Settings"
    _rec_name = "user_id"

    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        index=False,
        ondelete="cascade",
        domain=[("res_users_settings_id", "=", False)],
    )

    _unique_user_id = models.Constraint(
        "UNIQUE(user_id)",
        "One user should only have one user settings.",
    )

    @api.model
    def _get_fields_blacklist(self) -> list[str]:
        """Get list of fields that won't be formatted."""
        return ["display_name"]

    @api.model
    def _find_or_create_for_user(self, user: Any) -> Self:
        """Return the settings record for *user*, creating one if absent.

        When the current cursor is read-only (e.g. called from a readonly
        HTTP route), fall back to an in-memory record so that callers can
        still format the settings without triggering a write on a RO cursor.
        """
        settings = user.sudo().res_users_settings_ids
        if not settings:
            if self.env.cr.readonly:
                settings = self.sudo().new({"user_id": user.id})
            else:
                settings = self.sudo().create({"user_id": user.id})
        return settings

    def _res_users_settings_format(
        self, fields_to_format: list[str] | None = None
    ) -> dict[str, Any]:
        self.ensure_one()
        fields_blacklist = self._get_fields_blacklist()
        if fields_to_format:
            fields_to_format = [
                field for field in fields_to_format if field not in fields_blacklist
            ]
        else:
            fields_to_format = [
                name
                for name, field in self._fields.items()
                if name == "id"
                or (name not in models.MAGIC_COLUMNS and name not in fields_blacklist)
            ]
        return self._format_settings(fields_to_format)

    def _format_settings(self, fields_to_format: list[str]) -> dict[str, Any]:
        res = self._read_format(
            fnames=[fname for fname in fields_to_format if fname != "user_id"]
        )[0]
        if "user_id" in fields_to_format:
            res["user_id"] = {"id": self.user_id.id}
        return res

    # Fields that must never be set via `set_res_users_settings`.
    _PROTECTED_SETTINGS_FIELDS = frozenset({"user_id", "id", *models.MAGIC_COLUMNS})

    def set_res_users_settings(self, new_settings: dict[str, Any]) -> dict[str, Any]:
        self.ensure_one()
        changed_settings = {}
        for setting in new_settings:
            if setting in self._PROTECTED_SETTINGS_FIELDS:
                continue
            field = self._fields.get(setting)
            if not field or (field.compute and not field.inverse):
                continue
            current_value = self[setting]
            new_value = new_settings[setting]
            # For relational fields, compare IDs rather than recordset vs int
            if isinstance(current_value, models.BaseModel):
                current_value = current_value.id
            if new_value != current_value:
                changed_settings[setting] = new_value
        self.write(changed_settings)
        return self._res_users_settings_format([*changed_settings.keys(), "id"])
