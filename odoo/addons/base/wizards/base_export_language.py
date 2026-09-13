import ast
import base64
import io
from typing import Any

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools.translate import trans_export, trans_export_records

_debug = DebugLog(__name__)

NEW_LANG_KEY = "__new__"


class BaseLanguageExport(models.TransientModel):
    _name = "base.language.export"
    _description = "Language Export"

    @api.model
    def _selection_installed_langs(self) -> list[tuple[str, str]]:
        langs = self.env["res.lang"].get_installed()
        return [
            (
                NEW_LANG_KEY,
                self.env._("New Language (Empty translation template)"),
            )
        ] + langs

    name = fields.Char(
        string="File Name",
        readonly=True,
    )
    lang = fields.Selection(
        selection=_selection_installed_langs,
        string="Language",
        default=NEW_LANG_KEY,
        required=True,
    )
    format = fields.Selection(
        selection=[("csv", "CSV File"), ("po", "PO File"), ("tgz", "TGZ Archive")],
        string="File Format",
        default="po",
        required=True,
    )
    export_type = fields.Selection(
        selection=[("module", "Module"), ("model", "Model")],
        default="module",
        required=True,
    )
    modules = fields.Many2many(
        comodel_name="ir.module.module",
        relation="rel_modules_langexport",
        column1="wiz_id",
        column2="module_id",
        string="Apps To Export",
        domain=[("state", "=", "installed")],
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model to Export",
        domain=[("transient", "=", False)],
    )
    model_name = fields.Char(
        related="model_id.model",
        string="Model Name",
    )
    domain = fields.Char(
        string="Model Domain",
        default="[]",
    )
    data = fields.Binary(
        string="File",
        attachment=False,
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("choose", "choose"),
            ("get", "get"),
        ],
        default="choose",
    )

    def action_export_language_file(self) -> dict[str, Any]:
        self.check_singleton()
        lang = self.lang if self.lang != NEW_LANG_KEY else False
        mods = None

        with io.BytesIO() as buf:
            if self.export_type == "model":
                if not self.model_name:
                    raise UserError(_("Please select a model to export."))
                try:
                    domain = ast.literal_eval(self.domain or "[]")
                except ValueError, SyntaxError, TypeError:
                    raise UserError(
                        _("Invalid domain filter: %s", self.domain)
                    ) from None
                if not isinstance(domain, list):
                    raise UserError(_("Invalid domain filter: %s", self.domain))
                ids = self.env[self.model_name].search(domain).ids
                _debug.logic(
                    "export_records_selected", model=self.model_name, records=len(ids)
                )
                is_exported = trans_export_records(
                    lang, self.model_name, ids, buf, self.format, self.env
                )
            else:
                mods = sorted(self.mapped("modules.name")) or ["all"]
                is_exported = trans_export(lang, mods, buf, self.format, self.env)
            _debug.pipeline(
                "export_language",
                lang=lang,
                type=self.export_type,
                format=self.format,
                modules=mods,
                model=self.model_name,
                exported=bool(is_exported),
                bytes=buf.tell(),
            )
            out = base64.encodebytes(buf.getvalue()) if is_exported else False

        filename = "new"
        if lang:
            filename = tools.get_iso_codes(lang)
        elif self.export_type == "model":
            filename = self.model_name.replace(".", "_")
        elif mods and len(mods) == 1:
            filename = mods[0]
        extension = self.format
        if not lang and extension == "po":
            extension = "pot"
        name = f"{filename}.{extension}"

        _debug.lifecycle("export_file_ready", name=name, exported=bool(out))
        self.write({"state": "get", "data": out, "name": name})
        return {
            "name": self.env.ref("base.action_wizard_lang_export").name,
            "type": "ir.actions.act_window",
            "res_model": "base.language.export",
            "view_mode": "form",
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
        }
