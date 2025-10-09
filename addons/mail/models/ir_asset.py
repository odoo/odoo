# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

# Models whose definitions should be fetched when building JS model definitions.
# This includes models whose relations need to be preserved in the final output.
MODELS_TO_INCLUDE = [
    "discuss.call.history",
    "discuss.channel",
<<<<<<< Updated upstream
    "mail.followers",
    "mail.link.preview",
=======
    "discuss.channel.member",
    "discuss.channel.rtc.session",
    "ir.attachment",
    "mail.activity",
>>>>>>> Stashed changes
    "mail.activity.type",
    "mail.canned.response",
    "mail.followers",
    "mail.guest",
    "mail.link.preview",
    "mail.message",
    "mail.message.link.preview",
    "mail.message.subtype",
    "mail.notification",
    "mail.scheduled.message",
    "mail.template",
    "mail.thread",
    "res.company",
    "res.country",
    "res.groups",
    "res.groups.privilege",
    "res.lang",
    "res.partner",
    "res.role",
    "res.users",
]

# Models that should actually be included in the "mail.assets_js_model" bundle.
# This allows incremental conversion of JS model definitions to Python definitions,
# so new models can be progressively exposed without fetching everything.
MODELS_TO_EXPOSE = [
    "mail.activity",
    "mail.message",
    "mail.message.link.preview",
]


class IrAsset(models.Model):
    _inherit = "ir.asset"

    def _py_def_to_js_class(self, py_name, js_name, fields):
        type_map = {
            "many2one": "One",
            "many2many": "Many",
            "one2many": "Many",
            "html": "Html",
            "datetime": "Datetime",
            "date": "Date",
        }
        field_lines = []
        func_lines = []
        for field in sorted(fields.values(), key=lambda f: f["name"]):
            fname = field["name"]
            js_type = type_map.get(field["type"], "Attr")
            relation = f'"{field["relation"]}"' if field.get("relation") else "undefined"
            inverse = field.get("inverse_fname_by_model_name", {}).get(field.get("relation"))
            inverse_formatted = f'"{inverse}"' if inverse else "undefined"
            on_update_func_name = f"_{fname}_onUpdate"
            on_add_func_name = f"_{fname}_onAdd"
            on_delete_func_name = f"_{fname}_onDelete"
            func_lines.append(f"    {on_add_func_name}(record) {{}}")
            func_lines.append(f"    {on_update_func_name}(record) {{}}")
            func_lines.append(f"    {on_delete_func_name}(record) {{}}")
            field_lines.append(
                f"    {fname} = fields.{js_type}({relation}, {{inverse: {inverse_formatted}, onAdd: this.{on_add_func_name}.bind(this), onUpdate: this.{on_update_func_name}.bind(this), onDelete: this.{on_delete_func_name}.bind(this)}});"
            )
        js_class_lines = [
            f"class {js_name} extends Record {{",
            '    static id = "id";',
            f'    static _name = "{py_name}";',
            "",
        ]
        js_class_lines.extend(field_lines)
        js_class_lines.append("")
        js_class_lines.extend(func_lines)
        js_class_lines.append("}")
        js_class_lines.append(f"{js_name}.register();")
        return "\n".join(js_class_lines)

    def _register_hook(self):
        super()._register_hook()
        model_defs = self.env["ir.model"]._get_model_definitions(MODELS_TO_INCLUDE)
        js_lines = [
            'odoo.define("@mail/core/common/model_definitions", ["@mail/core/common/record"], function (require) {',
            "    'use strict';",
            "     const { fields, Record } = require('@mail/core/common/record');",
        ]
        classes_to_export = []
        for py_name, definition in sorted(model_defs.items(), key=lambda item: item[0]):
            if py_name not in MODELS_TO_EXPOSE:
                continue
            js_name = "".join(word.capitalize() for word in py_name.split("."))
            js_definition = self._py_def_to_js_class(py_name, js_name, definition["fields"])
            js_lines.append(js_definition)
            js_lines.append("")
            classes_to_export.append(js_name)
        js_lines.append("return {" + ", ".join(classes_to_export) + "};")
        js_lines.append("});")
        self._save_model_definition("\n".join(js_lines))

    def _save_model_definition(self, js_file_content):
        file_name = "model_definitions.js"
        bundle = "mail.assets_js_models"
        url = f"/mail/static/src/core/common/{file_name}"
        file_url = f"/{bundle}{url}"
        raw_file_content = js_file_content.encode()
        if existing_attachment := self.env["ir.attachment"].search([("name", "=", file_name)]):
            if existing_attachment.checksum != self.env["ir.attachment"]._compute_checksum(
                raw_file_content
            ):
                existing_attachment.raw = raw_file_content
            return
        self.env["ir.attachment"].create(
            {
                "raw": raw_file_content,
                "mimetype": "text/javascript",
                "name": file_name,
                "type": "binary",
                "url": file_url,
            },
        )
        self.env["ir.asset"].create(
            {
                "name": f"inject {file_name}",
                "path": file_url,
                "target": url,
                "directive": "append",
                "bundle": self.env["ir.asset"]._get_related_bundle(url, bundle),
            },
        )
