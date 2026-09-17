from odoo import SUPERUSER_ID, _, models, tools
from odoo.exceptions import UserError
from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.base.models.res_lang import LangData, LangDataDict

_debug = DebugLog(__name__)


class ResLang(models.Model):
    _inherit = "res.lang"

    def write(self, vals):
        if "active" in vals and not vals["active"] and self.env.uid != SUPERUSER_ID:
            if self.env["website"].search_count(
                [("language_ids", "in", self._ids)], limit=1
            ):
                _debug.logic(
                    "lang_deactivation_refused", reason="used_by_website", langs=self
                )
                raise UserError(
                    _(
                        "Cannot deactivate a language that is currently used on a website."
                    )
                )
        return super().write(vals)

    @tools.ormcache(
        'self.env.context.get("website_id")',
        'self.env.context.get("web_force_installed_langs")',
    )
    def _get_frontend(self) -> LangDataDict:
        if request and getattr(request, "is_frontend", True):
            if self.env.context.get("web_force_installed_langs"):
                langs = sorted(
                    map(dict, self._get_active_by_field("code").values()),
                    key=lambda lang: lang["name"],
                )
            else:
                lang_ids = (
                    self.env["website"]
                    .get_current_website()
                    .with_context(lang=False)
                    .language_ids.sorted("name")
                    .ids
                )
                langs = [
                    dict(self.env["res.lang"]._get_data(id=id_)) for id_ in lang_ids
                ]
            es_419_exists = any(lang["code"] == "es_419" for lang in langs)
            already_shortened = []
            for lang in langs:
                code = lang["code"]
                short_code = code.split("_")[0]
                if short_code not in already_shortened and not (
                    short_code == "es" and code != "es_419" and es_419_exists
                ):
                    lang["hreflang"] = short_code
                    already_shortened.append(short_code)
                else:
                    lang["hreflang"] = code.lower().replace("_", "-")
            _debug.perf.count(
                "frontend_langs_computed",
                website=self.env.context.get("website_id"),
                langs=len(langs),
            )
            return LangDataDict({lang["code"]: LangData(lang) for lang in langs})

        return super()._get_frontend()

    def action_activate_langs(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Add languages"),
            "view_mode": "form",
            "res_model": "base.language.install",
            "views": [[False, "form"]],
            "target": "new",
        }
