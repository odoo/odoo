# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import models
from odoo.addons.mail.tools.mail_js_models_registry import (
    BLACKLISTED_FIELDS_BY_MODEL,
    MODELS_TO_EXPOSE,
    MODELS_TO_INCLUDE,
)


class IrAsset(models.Model):
    _inherit = "ir.asset"

    def _py_def_to_js_class(self, py_name, js_name, fields) -> str:
        type_map = {
            "many2one": "One",
            "many2many": "Many",
            "one2many": "Many",
            "html": "Html",
            "datetime": "Datetime",
            "date": "Date",
        }
        field_definitions = []
        function_definitions = []
        for field in sorted(fields.values(), key=lambda f: f["name"]):
            fname = field["name"]
            js_type = type_map.get(field["type"], "Attr")
            relation = field.get("relation")
            relation_formatted = f'"{relation}"' if relation else "undefined"
            inverse = field.get("inverse_fname_by_model_name", {}).get(relation)
            inverse_formatted = f'"{inverse}"' if inverse else "undefined"

            compute_func_name = f"_compute_{fname}"
            on_update_func_name = f"_{fname}_onUpdate"
            on_add_func_name = f"_{fname}_onAdd"
            on_delete_func_name = f"_{fname}_onDelete"
            sort_func_name = f"_sort_{fname}"

            options = [
                f"inverse: {inverse_formatted},",
                f"compute() {{ return this.{compute_func_name}(); }},",
                f"onUpdate(record) {{ return this.{on_update_func_name}(record); }},",
            ]
            if relation:
                options.append(f"onAdd(record) {{ return this.{on_add_func_name}(record); }},")
                options.append(
                    f"onDelete(record) {{ return this.{on_delete_func_name}(record); }},"
                )
            if relation in ("many2many", "one2many"):
                options.append(f"sort() {{ return this.{sort_func_name}(); }},")
            field_definitions.append(f"    {fname} = fields.{js_type}({relation_formatted}, {{")
            for option in options:
                field_definitions.append(f"        {option}")
            field_definitions.append("    });")

            function_definitions.append(f"    {compute_func_name}() {{ return NO_COMPUTE_SYM; }}")
            function_definitions.append(f"    {on_update_func_name}(record) {{}}")
            if relation:
                function_definitions.append(f"    {on_add_func_name}(record) {{}}")
                function_definitions.append(f"    {on_delete_func_name}(record) {{}}")
            if relation in ("many2many", "one2many"):
                function_definitions.append(f"    {sort_func_name}() {{}}")

        js_class_lines = [
            f"class {js_name} extends Record {{",
            '    static id = "id";',
            f'    static _name = "{py_name}";',
            "",
        ]
        js_class_lines.extend(field_definitions)
        js_class_lines.append("")
        js_class_lines.extend(function_definitions)
        js_class_lines.append("}")
        if py_name != "ir.attachment":  # IrAttachment is extended by the FileMixin.
            js_class_lines.append(f"{js_name}.register();")
        return "\n".join(js_class_lines)

    def _register_hook(self):
        super()._register_hook()
        model_defs = self.env["ir.model"]._get_model_definitions(
            MODELS_TO_INCLUDE, BLACKLISTED_FIELDS_BY_MODEL
        )
        js_lines = [
            'odoo.define("@mail/core/common/model_definitions", ["@mail/core/common/record", "@mail/model/misc"], function (require) {',
            "    'use strict';",
            "     const { fields, Record } = require('@mail/core/common/record');",
            "     const { NO_COMPUTE_SYM } = require('@mail/model/misc');",
        ]
        classes_to_export = []
        for py_name, fields in sorted(model_defs.items(), key=lambda item: item[0]):
            if py_name not in MODELS_TO_EXPOSE:
                continue
            js_name = "".join(word.capitalize() for word in re.split(r"[._]", py_name))
            js_definition = self._py_def_to_js_class(py_name, js_name, fields)
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
