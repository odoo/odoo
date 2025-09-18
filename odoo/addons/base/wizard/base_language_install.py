from typing import Any

from odoo import api, fields, models


class BaseLanguageInstall(models.TransientModel):
    _name = "base.language.install"
    _description = "Install Language"

    @api.model
    def _default_lang_ids(self) -> list[int] | bool:
        """Display the selected language when using the 'Update Terms' action
        from the language list view
        """
        if self.env.context.get("active_model") == "res.lang":
            if ids := self.env.context.get("active_ids"):
                return ids
            if active_id := self.env.context.get("active_id"):
                return [active_id]
        return False

    # add a context on the field itself, to be sure even inactive langs are displayed
    lang_ids = fields.Many2many(
        "res.lang",
        "res_lang_install_rel",
        "language_wizard_id",
        "lang_id",
        "Languages",
        default=_default_lang_ids,
        context={"active_test": False},
        required=True,
    )
    overwrite = fields.Boolean(
        "Overwrite Existing Terms",
        default=True,
        help="If you check this box, your customized translations will be overwritten and replaced by the official ones.",
    )
    first_lang_id = fields.Many2one(
        "res.lang",
        compute="_compute_first_lang_id",
        help="Used when the user only selects one language and is given the option to switch to it",
    )

    def _compute_first_lang_id(self) -> None:
        self.first_lang_id = False
        for lang_installer in self.filtered("lang_ids"):
            lang_installer.first_lang_id = lang_installer.lang_ids[0]

    def lang_install(self) -> dict[str, Any]:
        self.ensure_one()
        mods = self.env["ir.module.module"].search([("state", "=", "installed")])
        self.lang_ids.active = True
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

    def switch_lang(self) -> dict[str, str]:
        self.env.user.lang = self.first_lang_id.code
        return {
            "type": "ir.actions.client",
            "tag": "reload_context",
        }
