from typing import Any

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResUsersSettingsEmbeddedAction(models.Model):
    _name = "res.users.settings.embedded.action"
    _description = "User Settings for Embedded Actions"

    user_setting_id = fields.Many2one(
        comodel_name="res.users.settings",
        export_string_translation=False,
        index="btree_not_null",
        required=True,
        ondelete="cascade",
    )
    action_id = fields.Many2one(
        comodel_name="ir.actions.act_window",
        export_string_translation=False,
        required=True,
        ondelete="cascade",
    )
    res_model = fields.Char(
        export_string_translation=False,
        required=True,
    )
    res_id = fields.Integer(export_string_translation=False)
    embedded_actions_order = fields.Char(
        string="List order of embedded action ids",
        export_string_translation=False,
    )
    embedded_actions_visibility = fields.Char(
        string="List visibility of embedded actions ids",
        export_string_translation=False,
    )
    embedded_visibility = fields.Boolean(
        string="Is top bar visible",
        export_string_translation=False,
    )

    _res_user_settings_embedded_action_unique = models.UniqueIndex(
        "(user_setting_id, action_id, res_id) WHERE res_id IS NOT NULL",
        "The user should have one unique embedded action setting per user setting, action and record id.",
    )

    @api.constrains("embedded_actions_order")
    def _check_embedded_actions_order(self) -> None:
        self._check_embedded_actions_field_format("embedded_actions_order")

    @api.constrains("embedded_actions_visibility")
    def _check_embedded_actions_visibility(self) -> None:
        self._check_embedded_actions_field_format("embedded_actions_visibility")

    def _check_embedded_actions_field_format(self, field_name: str) -> None:
        for setting in self:
            value = setting[field_name]
            if not value:
                continue
            action_ids = value.split(",")
            if len(action_ids) != len(set(action_ids)):
                raise ValidationError(
                    self.env._(
                        "The ids in %(field_name)s must not be duplicated: “%(action_ids)s”",
                        field_name=field_name,
                        action_ids=action_ids,
                    )
                )
            for action_id in action_ids:
                if not (action_id.isdecimal() or action_id == "false"):
                    raise ValidationError(
                        self.env._(
                            'The ids in %(field_name)s must only be integers or "false": “%(action_ids)s”',
                            field_name=field_name,
                            action_ids=action_ids,
                        )
                    )

    @staticmethod
    def _parse_id_list(value: str) -> list[int | bool]:
        if not value:
            return []
        return [False if token == "false" else int(token) for token in value.split(",")]

    def _format_embedded_action_settings(self) -> dict[str, dict[str, Any]]:
        return {
            f"{setting.action_id.id}+{setting.res_id or ''}": {
                "embedded_actions_order": self._parse_id_list(
                    setting.embedded_actions_order
                ),
                "embedded_actions_visibility": self._parse_id_list(
                    setting.embedded_actions_visibility
                ),
                "embedded_visibility": setting.embedded_visibility,
            }
            for setting in self
        }
