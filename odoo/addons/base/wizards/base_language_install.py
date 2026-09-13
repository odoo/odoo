from typing import Any

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class BaseLanguageInstall(models.TransientModel):
    _name = "base.language.install"
    _description = "Install Language"

    @api.model
    def _default_lang_ids(self) -> list[int] | bool:
        if self.env.context.get("active_model") == "res.lang":
            if ids := self.env.context.get("active_ids"):
                return ids
            if active_id := self.env.context.get("active_id"):
                return [active_id]
        return False

    lang_ids = fields.Many2many(
        comodel_name="res.lang",
        relation="res_lang_install_rel",
        column1="language_wizard_id",
        column2="lang_id",
        string="Languages",
        default=_default_lang_ids,
        required=True,
        context={"active_test": False},
    )
    overwrite = fields.Boolean(
        string="Overwrite Existing Terms",
        default=True,
        help="If you check this box, your customized translations will be overwritten and replaced by the official ones.",
    )
    first_lang_id = fields.Many2one(
        comodel_name="res.lang",
        compute="_compute_first_lang_id",
        help="Used when the user only selects one language and is given the option to switch to it",
    )

    @api.depends("lang_ids")
    def _compute_first_lang_id(self) -> None:
        self.first_lang_id = False
        for lang_installer in self.filtered("lang_ids"):
            lang_installer.first_lang_id = lang_installer.lang_ids[0]

    def action_install_lang(self) -> dict[str, Any]:
        self.check_singleton()
        mods = self.env["ir.module.module"].search([("state", "=", "installed")])
        _debug.lifecycle("langs_activated", langs=self.lang_ids.mapped("code"))
        self.lang_ids.active = True
        with _debug.perf(
            "install_langs",
            cr=self.env.cr,
            langs=self.lang_ids.mapped("code"),
            modules=len(mods),
            overwrite=self.overwrite,
        ):
            mods._update_translations(self.lang_ids.mapped("code"), self.overwrite)

        if len(self.lang_ids) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "base.language.install",
                "res_id": self.id,
                "view_mode": "form",
                "target": "new",
                "views": [
                    [
                        self.env.ref("base.language_install_view_form_lang_switch").id,
                        "form",
                    ]
                ],
            }

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "context": dict(self.env.context, active_ids=self.ids),
            "target": "new",
            "params": {
                "message": self.env._(
                    "The languages that you selected have been successfully installed. "
                    "Users can choose their favorite language in their preferences."
                ),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def reload(self) -> dict[str, str]:
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def action_switch_lang(self) -> dict[str, str]:
        _debug.lifecycle(
            "user_lang_switched", uid=self.env.uid, lang=self.first_lang_id.code
        )
        self.env.user.lang = self.first_lang_id.code
        return {
            "type": "ir.actions.client",
            "tag": "reload_context",
        }
