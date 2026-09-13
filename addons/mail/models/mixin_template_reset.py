import json
from typing import Self

from lxml import etree

from odoo import _, api, fields, models
from odoo.api import ValuesType
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.modules.module import get_resource_from_path
from odoo.tools.convert import xml_import
from odoo.tools.misc import file_path
from odoo.tools.translate import TranslationImporter, get_po_paths

_debug = DebugLog(__name__)


class MixinTemplateReset(models.AbstractModel):
    _name = "mixin.template.reset"
    _description = "Template Reset Mixin"

    template_fs = fields.Char(
        string="Template Filename",
        copy=False,
        help="""File from where the template originates. Used to reset broken template.""",
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        for vals in vals_list:
            if "template_fs" not in vals and "install_filename" in self.env.context:
                path_info = get_resource_from_path(self.env.context["install_filename"])
                if path_info:
                    vals["template_fs"] = path_info.addons_path
        return super().create(vals_list)

    def _load_records_write(self, values: dict) -> None:
        if self.env.context.get("reset_template"):
            fields_in_xml_record = values.keys()
            fields_not_to_touch = (
                set(models.MAGIC_COLUMNS) | fields_in_xml_record | {"template_fs"}
            )
            fields_to_empty = self._fields.keys() - fields_not_to_touch
            field_defaults = self.default_get(list(fields_to_empty))
            values.update(field_defaults)
            fields_to_empty -= set(field_defaults.keys())
            values.update(dict.fromkeys(fields_to_empty, False))
        return super()._load_records_write(values)

    def _override_translation_term(self, module_name: str, xml_ids: list[str]) -> None:
        translation_importer = TranslationImporter(self.env.cr)

        for lang, _name in self.env["res.lang"].get_installed():
            for po_path in get_po_paths(module_name, lang):
                translation_importer.load_file(po_path, lang, xmlids=xml_ids)

        translation_importer.save(overwrite=True, force_overwrite=True)

    def reset_template(self) -> None:
        expr = "//*[local-name() = $tag and (@id = $xml_id or @id = $external_id)]"
        templates_with_missing_source = []
        lang_false = {
            code: False
            for code, _ in self.env["res.lang"].get_installed()
            if code != "en_US"
        }
        for template in self.filtered("template_fs"):
            external_id = template.get_external_id().get(template.id)
            module, xml_id = external_id.split(".")
            fullpath = file_path(template.template_fs)
            _debug.lifecycle(
                "template_reset",
                model=self._name,
                record=template.id,
                xmlid=external_id,
                source_found=bool(fullpath),
            )
            if fullpath:
                for field_name, field in template._fields.items():
                    if field.translate is True:
                        template.update_field_translations(field_name, lang_false)
                doc = etree.parse(fullpath)
                for rec in doc.xpath(
                    expr, tag="record", xml_id=xml_id, external_id=external_id
                ):
                    rec.set("context", json.dumps({"reset_template": "True"}))
                    obj = xml_import(
                        template.env, module, {}, mode="init", xml_filename=fullpath
                    )
                    obj._tag_record(rec)
                    template._override_translation_term(module, [xml_id, external_id])
            else:
                templates_with_missing_source.append(template.display_name)
        if templates_with_missing_source:
            raise UserError(
                _(
                    "The following email templates could not be reset because their related source files could not be found:\n- %s",
                    "\n- ".join(templates_with_missing_source),
                )
            )
