import logging
from collections import defaultdict
from collections.abc import Collection
from typing import TYPE_CHECKING, Any

from odoo import api, models
from odoo.libs.debug_log import DebugLog

if TYPE_CHECKING:
    from odoo.addons.base.models.ir_model import IrModel
    from odoo.addons.base.models.ir_module import IrModuleModule

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class ReportWebReport_Irmodulereference(models.AbstractModel):
    _name = "report.web.report_irmodulereference"
    _description = "Module Reference Report"

    def _get_models_by_module(self, modules: IrModuleModule) -> dict[str, IrModel]:
        data = (
            self.env["ir.model.data"]
            .sudo()
            .search(
                [("model", "=", "ir.model"), ("module", "in", modules.mapped("name"))]
            )
        )
        ids_by_module = defaultdict(list)
        for record in data:
            ids_by_module[record.module].append(record.res_id)

        model_records = self.env["ir.model"]
        return {
            module.name: model_records.browse(ids_by_module[module.name])
            .exists()
            .sorted("model")
            for module in modules
        }

    def _get_field_names_by_model(
        self, modules: IrModuleModule
    ) -> dict[str, dict[str, set[str]]]:
        data = (
            self.env["ir.model.data"]
            .sudo()
            .search(
                [
                    ("model", "=", "ir.model.fields"),
                    ("module", "in", modules.mapped("name")),
                ]
            )
        )
        live_fields = self.env["ir.model.fields"].browse(data.mapped("res_id")).exists()
        spec_by_id = {field.id: (field.model, field.name) for field in live_fields}

        names: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        for record in data:
            if spec := spec_by_id.get(record.res_id):
                model_name, field_name = spec
                names[record.module][model_name].add(field_name)
        return names

    def _get_field_descriptions(
        self, model_name: str, field_names: Collection[str]
    ) -> list[dict[str, Any]]:
        if not field_names:
            return []
        model = self.env.get(model_name)
        if model is None:
            return []
        try:
            with self.env.cr.savepoint(flush=False):
                descriptions = model.fields_get(field_names)
        except Exception:
            _logger.warning(
                "Cannot describe the fields of %s; reporting it without them.",
                model_name,
                exc_info=True,
            )
            _debug.logic(
                "field_descriptions_failed", model=model_name, fields=len(field_names)
            )
            return []
        return [
            {
                "name": name,
                "string": description.get("string", name),
                "type": description.get("type", ""),
                "required": description.get("required", False),
                "readonly": description.get("readonly", False),
                "help": description.get("help", ""),
            }
            for name, description in sorted(descriptions.items())
        ]

    @api.model
    def _get_report_values(
        self, docids: list[int] | None, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        modules = self.env["ir.module.module"].browse(docids)
        with _debug.perf("report_values", cr=self.env.cr, modules=len(modules)) as span:
            models_by_module = self._get_models_by_module(modules)
            names_by_module = self._get_field_names_by_model(modules)
            span.set(models=sum(len(m) for m in models_by_module.values()))

        objects_by_module = {}
        for module in modules:
            field_names = names_by_module.get(module.name, {})
            objects_by_module[module.name] = [
                {
                    "model": record.model,
                    "name": record.name,
                    "fields": self._get_field_descriptions(
                        record.model, field_names.get(record.model, ())
                    ),
                }
                for record in models_by_module[module.name]
            ]

        return {
            "doc_ids": docids,
            "doc_model": "ir.module.module",
            "docs": modules,
            "objects_by_module": objects_by_module,
        }
