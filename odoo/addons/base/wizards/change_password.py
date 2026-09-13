from typing import Any

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog

from ..models.res_users import check_identity

_debug = DebugLog(__name__)


class ChangePasswordWizard(models.TransientModel):
    _name = "change.password.wizard"
    _description = "Change Password Wizard"
    _transient_max_hours = 0.2

    def _default_user_ids(self) -> list[tuple[int, int, dict[str, Any]]]:
        user_ids = (
            self.env.context.get("active_model") == "res.users"
            and self.env.context.get("active_ids")
        ) or []
        return [
            Command.create({"user_id": user.id, "user_login": user.login})
            for user in self.env["res.users"].browse(user_ids)
        ]

    user_ids = fields.One2many(
        comodel_name="change.password.user",
        inverse_name="wizard_id",
        string="Users",
        default=_default_user_ids,
    )

    def change_password_button(self) -> dict[str, str]:
        self.check_singleton()
        self.user_ids.change_password_button()
        if self.env.user in self.user_ids.user_id:
            return {"type": "ir.actions.client", "tag": "reload"}
        return {"type": "ir.actions.act_window_close"}


class ChangePasswordUser(models.TransientModel):
    _name = "change.password.user"
    _description = "User, Change Password Wizard"
    wizard_id = fields.Many2one(
        comodel_name="change.password.wizard",
        required=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
        ondelete="cascade",
    )
    user_login = fields.Char(readonly=True)
    new_passwd = fields.Char(
        string="New Password",
        default="",
    )

    def change_password_button(self) -> None:
        _debug.lifecycle(
            "wizard_change_password",
            by=self.env.uid,
            users=[line.user_id.id for line in self if line.new_passwd],
        )
        for line in self:
            if line.new_passwd:
                line.user_id._change_password(line.new_passwd)
        self.write({"new_passwd": False})


class ChangePasswordOwn(models.TransientModel):
    _name = "change.password.own"
    _description = "User, change own password wizard"
    _transient_max_hours = 0.1

    new_password = fields.Char()
    confirm_password = fields.Char(string="New Password (Confirmation)")

    @api.constrains("new_password", "confirm_password")
    def _check_password_confirmation(self) -> None:
        for record in self:
            if record.confirm_password != record.new_password:
                raise ValidationError(
                    _("The new password and its confirmation must be identical.")
                )

    @check_identity
    def change_password(self) -> dict[str, str]:
        self.env.user._change_password(self.new_password or "")
        self.unlink()
        return {"type": "ir.actions.client", "tag": "reload"}
