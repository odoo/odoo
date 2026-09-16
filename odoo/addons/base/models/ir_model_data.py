import logging
import random
import typing
from collections import defaultdict
from operator import itemgetter
from typing import Any, Self

import psycopg

from odoo import api, fields, models, tools
from odoo.api import ValuesType
from odoo.exceptions import AccessError, MissingError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.models import add_field
from odoo.tools import SQL, groupby, reset_cached_properties, unique
from odoo.tools.translate import _

from .ir_model_common import MODULE_UNINSTALL_FLAG

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class IrModelData(models.Model):
    _name = "ir.model.data"
    _is_registry_metadata = True
    _description = "Model Data"
    _order = "module, model, name"
    _allow_sudo_commands = False

    name = fields.Char(
        string="External Identifier",
        required=True,
        help="External Key/Identifier that can be used for data integration with third-party systems",
    )
    complete_name = fields.Char(
        string="Complete ID",
        compute="_compute_complete_name",
    )
    model = fields.Char(
        string="Model Name",
        required=True,
    )
    module = fields.Char(
        default="",
        required=True,
    )
    res_id = fields.Many2oneReference(
        model_field="model",
        string="Record ID",
        help="ID of the target record in the database",
    )
    noupdate = fields.Boolean(
        string="Non Updatable",
        default=False,
    )
    reference = fields.Char(
        compute="_compute_reference",
        store=False,
        readonly=True,
    )

    _name_nospaces = models.Constraint(
        "CHECK(name NOT LIKE '% %')", "External IDs cannot contain spaces"
    )
    _module_name_uniq_index = models.UniqueIndex("(module, name)")
    _model_res_id_index = models.Index("(model, res_id)")

    @api.depends("module", "name")
    def _compute_complete_name(self) -> None:
        for res in self:
            res.complete_name = ".".join(n for n in [res.module, res.name] if n)

    @api.depends("model", "res_id")
    def _compute_reference(self) -> None:
        for res in self:
            res.reference = f"{res.model},{res.res_id}"

    @api.depends("res_id", "model", "complete_name")
    def _compute_display_name(self) -> None:
        invalid_records = self.filtered(
            lambda r: not r.res_id or r.model not in self.env
        )
        for invalid_record in invalid_records:
            invalid_record.display_name = invalid_record.complete_name
        for model, model_data_records in (
            (self - invalid_records).grouped("model").items()
        ):
            records = self.env[model].browse(model_data_records.mapped("res_id"))
            for xid, target_record in zip(model_data_records, records, strict=True):
                try:
                    xid.display_name = target_record.display_name or xid.complete_name
                except AccessError, MissingError:
                    _debug.logic("display_name.fallback", xmlid=xid.id, model=model)
                    xid.display_name = xid.complete_name

    @api.model
    @tools.ormcache("xmlid", cache="xmlid")
    def _xmlid_target(self, xmlid: str) -> tuple[str, int] | None:
        if "." not in xmlid:
            _debug.logic("xmlid_miss", xmlid=xmlid, reason="no_module_prefix")
            return None
        module, name = xmlid.split(".", 1)
        data = self.sudo().search_fetch(
            [("module", "=", module), ("name", "=", name)], ["model", "res_id"], limit=1
        )
        if not (data and data.res_id):
            _debug.logic("xmlid_miss", xmlid=xmlid)
            return None
        _debug.perf.count("xmlid.cache_miss", xmlid=xmlid, model=data.model)
        return data.model, data.res_id

    @api.model
    def _get_xmlid_target(self, xmlid: str) -> tuple[str, int]:
        target = self._xmlid_target(xmlid)
        if target is None:
            raise ValueError(f"External ID not found in the system: {xmlid}")
        return target

    @api.model
    def _xmlid_to_res_model_res_id(
        self, xmlid: str, raise_if_not_found: bool = False
    ) -> tuple[str, int] | tuple[typing.Literal[False], typing.Literal[False]]:
        try:
            return self._get_xmlid_target(xmlid)
        except ValueError:
            if raise_if_not_found:
                raise
            return (False, False)

    @api.model
    def _xmlid_to_res_id(
        self, xmlid: str, raise_if_not_found: bool = False
    ) -> int | bool:
        return self._xmlid_to_res_model_res_id(xmlid, raise_if_not_found)[1]

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        vals_list = super().copy_data(default=default)
        for model, vals in zip(self, vals_list, strict=True):
            rand = f"{random.getrandbits(16):04x}"
            vals["name"] = f"{model.name}_{rand}"
        _debug.lifecycle("copy_data", count=len(vals_list))
        return vals_list

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        res = super().create(vals_list)
        _debug.lifecycle("create", count=len(res))
        self.env.registry.clear_cache("xmlid")
        if any(vals.get("model") == "res.groups" for vals in vals_list):
            _debug.logic("groups_cache_cleared", reason="create")
            self.env.registry.clear_cache("groups")
        return res

    def write(self, vals: dict[str, Any]) -> bool:
        if not self:
            return True
        bust_xmlid = not (set(vals) <= {"noupdate"})
        touch_groups = vals.get("model") == "res.groups" or any(
            data.model == "res.groups" for data in self
        )
        _debug.lifecycle(
            "write",
            count=len(self),
            fields=list(vals),
            bust_xmlid=bust_xmlid,
            touch_groups=touch_groups,
        )
        res = super().write(vals)
        if bust_xmlid:
            self.flush_recordset()
            self.env.registry.clear_cache("xmlid")
        if touch_groups:
            self.env.registry.clear_cache("groups")
        return res

    def unlink(self) -> bool:
        if not self:
            return True
        touch_groups = any(data.model == "res.groups" for data in self.exists())
        _debug.lifecycle("unlink", count=len(self), touch_groups=touch_groups)
        res = super().unlink()
        self.env.registry.clear_cache()
        if touch_groups:
            self.env.registry.clear_cache("groups")
        return res

    def _get_xmlids(self, xml_ids: list[str], model: Any) -> list[tuple]:
        if not xml_ids:
            _debug.logic("get_xmlids.skipped", model=model._name, reason="empty")
            return []

        bymodule = defaultdict(set)
        for xml_id in xml_ids:
            prefix, suffix = xml_id.split(".", 1)
            bymodule[prefix].add(suffix)

        domain = Domain.OR(
            Domain("module", "=", prefix) & Domain("name", "in", list(suffixes))
            for prefix, suffixes in bymodule.items()
        )
        rows = self.sudo().search_fetch(
            domain, ["module", "name", "model", "res_id", "noupdate"]
        )
        target_ids = set(
            model.browse(row.res_id for row in rows if row.model == model._name)
            .exists()
            .ids
        )
        result = [
            (
                row.id,
                row.module,
                row.name,
                row.model,
                row.res_id,
                row.noupdate,
                row.res_id if row.res_id in target_ids else None,
            )
            for row in rows
        ]
        _debug.perf.count(
            "get_xmlids",
            model=model._name,
            requested=len(xml_ids),
            modules=len(bymodule),
            found=len(result),
        )
        return result

    @api.model
    def _update_xmlids(
        self, data_list: list[dict[str, Any]], update: bool = False
    ) -> None:
        if not data_list:
            _debug.logic("update_xmlids.skipped", reason="empty")
            return

        rows: dict[tuple[str, str], tuple[str, int, bool]] = {}
        for data in data_list:
            prefix, suffix = data["xml_id"].split(".", 1)
            record = data["record"]
            rows[prefix, suffix] = (record._name, record.id, bool(data.get("noupdate")))

        bymodule = defaultdict(list)
        for prefix, suffix in rows:
            bymodule[prefix].append(suffix)
        existing = {
            (data.module, data.name): data
            for data in self.sudo().search_fetch(
                Domain.OR(
                    Domain("module", "=", prefix) & Domain("name", "in", names)
                    for prefix, names in bymodule.items()
                ),
                ["module", "name", "model", "res_id", "noupdate"],
            )
        }

        extra_vals = self._xmlid_extra_vals()
        to_create = []
        repointed = False
        for (prefix, suffix), (model_name, res_id, noupdate) in rows.items():
            data = existing.get((prefix, suffix))
            if data is None:
                to_create.append(
                    {
                        "module": prefix,
                        "name": suffix,
                        "model": model_name,
                        "res_id": res_id,
                        "noupdate": noupdate,
                        **extra_vals,
                    }
                )
            elif (data.model, data.res_id) != (model_name, res_id) and not (
                update and data.noupdate
            ):
                _debug.logic(
                    "update_xmlids.repointed",
                    xmlid=data.id,
                    old_model=data.model,
                    old_res_id=data.res_id,
                    model=model_name,
                    res_id=res_id,
                )
                data.write({"model": model_name, "res_id": res_id})
                repointed = True
        if to_create:
            self.sudo().create(to_create)
        _debug.pipeline(
            "update_xmlids",
            rows=len(rows),
            update=update,
            created=len(to_create),
            repointed=repointed,
        )
        # create() and write() above own the cache invalidation the raw upsert had to do here

        xml_ids = {f"{prefix}.{suffix}" for prefix, suffix in rows}
        self.pool.loaded_xmlids.update(xml_ids)
        self.pool.record_xmlids_written(xml_ids)

    def _xmlid_extra_vals(self) -> dict[str, Any]:
        return {}

    @api.model
    def _load_xmlid(self, xml_id: str) -> Any:
        record = self.env.ref(xml_id, raise_if_not_found=False)
        _debug.logic("load_xmlid", xmlid=xml_id, found=bool(record))
        if record:
            self.pool.loaded_xmlids.add(xml_id)
            self.pool.record_xmlids_written((xml_id,))
        return record

    @api.model
    def _uninstall_module_data(self, modules_to_remove: list[str]) -> None:
        if not self.env.is_system():
            _debug.logic(
                "uninstall_module_data.rejected", uid=self.env.uid, reason="not_system"
            )
            raise AccessError(
                _("Administrator access is required to uninstall a module")
            )

        self = self.with_context(
            **{MODULE_UNINSTALL_FLAG: True, "prefetch_fields": False}
        )

        module_data = self.search(
            [("module", "in", modules_to_remove)], order="id DESC"
        )
        records_items, model_ids, field_ids, selection_ids, constraint_ids = (
            self._partition_module_data(module_data)
        )
        _debug.pipeline(
            "uninstall_module_data",
            modules=modules_to_remove,
            xmlids=len(module_data),
            records=len(records_items),
            models=len(model_ids),
            fields=len(field_ids),
            selections=len(selection_ids),
            constraints=len(constraint_ids),
        )

        self._unshare_prefetched_fields(field_ids)

        undeletable_ids: list[int] = []

        for model, items in groupby(unique(records_items), itemgetter(0)):
            ids = [item[1] for item in items]
            if model in self.env:
                self._remove_uninstalled(
                    self.env[model].browse(ids), module_data, undeletable_ids
                )
            else:
                _debug.logic(
                    "uninstall_module_data.orphans", model=model, count=len(ids)
                )
                _logger.info(
                    "Orphan ir.model.data records %s refer to unavailable model '%s'",
                    ids,
                    model,
                )

        modules = self.env["ir.module.module"].search(
            [("name", "in", modules_to_remove)]
        )
        modules._remove_copied_views()

        self._remove_uninstalled(
            self.env["ir.model.constraint"].browse(unique(constraint_ids)),
            module_data,
            undeletable_ids,
        )
        self._remove_uninstalled(
            self.env["ir.model.fields.selection"]
            .browse(unique(selection_ids))
            .exists(),
            module_data,
            undeletable_ids,
        )
        self._remove_uninstalled(
            self.env["ir.model.fields"].browse(unique(field_ids)),
            module_data,
            undeletable_ids,
        )
        relations = self.env["ir.model.relation"].search(
            [("module", "in", modules.ids)]
        )
        _debug.pipeline("uninstall_module_data.relations", count=len(relations))
        relations._uninstall_module_data()

        self._remove_uninstalled(
            self.env["ir.model"].browse(unique(model_ids)),
            module_data,
            undeletable_ids,
        )

        _logger.info("ir.model.data could not be deleted (%s)", undeletable_ids)
        _debug.pipeline("uninstall_module_data_done", undeletable=len(undeletable_ids))
        self._remove_uninstalled_xmlids(module_data, undeletable_ids)

    @staticmethod
    def _partition_module_data(
        module_data: models.BaseModel,
    ) -> tuple[list[tuple[str, int]], list[int], list[int], list[int], list[int]]:
        records_items: list[tuple[str, int]] = []
        model_ids: list[int] = []
        field_ids: list[int] = []
        selection_ids: list[int] = []
        constraint_ids: list[int] = []
        for data in module_data:
            match data.model:
                case "ir.model":
                    model_ids.append(data.res_id)
                case "ir.model.fields":
                    field_ids.append(data.res_id)
                case "ir.model.fields.selection":
                    selection_ids.append(data.res_id)
                case "ir.model.constraint":
                    constraint_ids.append(data.res_id)
                case _:
                    records_items.append((data.model, data.res_id))
        return records_items, model_ids, field_ids, selection_ids, constraint_ids

    def _unshare_prefetched_fields(self, field_ids: list[int]) -> None:
        has_shared_field = False
        for ir_field in self.env["ir.model.fields"].browse(field_ids):
            model = self.pool.get(ir_field.model)
            if model is None:
                continue
            field = model._fields.get(ir_field.name)
            if field is None or not field.prefetch:
                continue
            if field._toplevel:
                _debug.logic(
                    "unshare_prefetch.toplevel", model=ir_field.model, field=field.name
                )
                field.prefetch = False
            else:
                _debug.logic(
                    "unshare_prefetch.shared", model=ir_field.model, field=field.name
                )
                Field = type(field)
                field_ = Field(_base_fields__=(field, Field(prefetch=False)))
                add_field(self.env.registry[ir_field.model], ir_field.name, field_)
                field_.setup(model)
                has_shared_field = True
        if has_shared_field:
            _debug.lifecycle("unshare_prefetch.registry_reset", fields=len(field_ids))
            reset_cached_properties(self.env.registry)

    def _remove_uninstalled(
        self,
        records: models.BaseModel,
        module_data: models.BaseModel,
        undeletable_ids: list[int],
    ) -> None:
        ref_data = self.search(
            [
                ("model", "=", records._name),
                ("res_id", "in", records.ids),
            ]
        )
        cloc_exclude_data = ref_data.filtered(
            lambda imd: imd.module == "__cloc_exclude__"
        )
        ref_data -= cloc_exclude_data
        records -= records.browse((ref_data - module_data).mapped("res_id"))
        _debug.logic(
            "remove_uninstalled",
            model=records._name,
            candidates=len(ref_data),
            deletable=len(records),
        )
        if not records:
            return

        if records._name == "ir.model.fields":
            records = self._remove_undeletable_fields(records, ref_data)

        _logger.info("Deleting %s", records)
        try:
            with self.env.cr.savepoint():
                cloc_exclude_data.unlink()
                with _debug.perf(
                    "remove_uninstalled.unlink",
                    cr=self.env.cr,
                    model=records._name,
                    count=len(records),
                ):
                    records.unlink()
        except Exception:
            _debug.logic(
                "remove_uninstalled_failed", model=records._name, count=len(records)
            )
            if len(records) <= 1:
                _debug.logic(
                    "remove_uninstalled.undeletable",
                    model=records._name,
                    xmlids=len(ref_data),
                )
                undeletable_ids.extend(ref_data._ids)
            else:
                _debug.logic(
                    "remove_uninstalled.bisect", model=records._name, count=len(records)
                )
                half_size = len(records) // 2
                self._remove_uninstalled(
                    records[:half_size], module_data, undeletable_ids
                )
                self._remove_uninstalled(
                    records[half_size:], module_data, undeletable_ids
                )

    def _remove_undeletable_fields(
        self, records: models.BaseModel, ref_data: models.BaseModel
    ) -> models.BaseModel:
        missing = records - records.exists()
        if missing:
            orphans = ref_data.filtered(lambda r: r.res_id in missing._ids)
            _debug.lifecycle(
                "undeletable_fields.orphans", missing=len(missing), orphans=len(orphans)
            )
            _logger.info("Deleting orphan ir_model_data %s", orphans)
            orphans.unlink()
            records -= missing
        records -= records.filtered(
            lambda f: (
                f.name == "id"
                or (
                    f.name in models.LOG_ACCESS_COLUMNS
                    and f.model in self.env
                    and self.env[f.model]._log_access
                )
            )
        )
        return records

    def _remove_uninstalled_xmlids(
        self, module_data: models.BaseModel, undeletable_ids: list[int]
    ) -> None:
        kept = 0  # debuglog
        unprobed = 0  # debuglog
        for data in self.browse(undeletable_ids).exists():
            if data.model not in self.env.registry:
                continue
            record = self.env[data.model].browse(data.res_id)
            try:
                with self.env.cr.savepoint():
                    if record.exists():
                        kept += 1  # debuglog
                        module_data -= data
                        continue
            except psycopg.ProgrammingError:
                unprobed += 1  # debuglog
                _debug.logic(
                    "remove_xmlids.exists_failed", model=data.model, res_id=data.res_id
                )
        _debug.lifecycle(
            "remove_xmlids",
            undeletable=len(undeletable_ids),
            kept=kept,
            unprobed=unprobed,
            removed=len(module_data),
        )
        module_data.unlink()

    def _count_xmlids_per_record(
        self, keys: list[tuple[str, int]]
    ) -> dict[tuple[str, int], int]:
        if not keys:
            return {}
        models_, res_ids = zip(*set(keys), strict=True)
        return {
            (model, res_id): count
            for model, res_id, count in self.env.execute_query(
                SQL(
                    """SELECT model, res_id, count(*)
                       FROM ir_model_data
                       WHERE (model, res_id) IN (
                           SELECT * FROM unnest(%s::varchar[], %s::integer[])
                       )
                       GROUP BY model, res_id""",
                    list(models_),
                    list(res_ids),
                )
            )
        }

    @api.model
    def _process_end_unlink_record(self, record: Any) -> None:
        record.unlink()

    @api.model
    def _process_end(self, modules: list[str]) -> None:
        if not modules or tools.config.get("import_partial"):
            _debug.logic(
                "process_end.skipped",
                reason="no_modules" if not modules else "import_partial",
            )
            return

        bad_imd_ids = []
        self = self.with_context({MODULE_UNINSTALL_FLAG: True})
        loaded_xmlids = self.pool.loaded_xmlids

        query = """ SELECT id, module || '.' || name, model, res_id FROM ir_model_data
                    WHERE module = ANY(%s) AND res_id IS NOT NULL AND COALESCE(noupdate, false) != %s ORDER BY id DESC
                """
        self.env.cr.execute(query, (list(modules), True))
        candidates = self.env.cr.fetchall()
        xmlids_per_record = self._count_xmlids_per_record(
            [(model, res_id) for _id, _xmlid, model, res_id in candidates]
        )
        _debug.pipeline(
            "process_end",
            modules=len(modules),
            candidates=len(candidates),
            loaded_xmlids=len(loaded_xmlids),
        )

        for id, xmlid, model, res_id in candidates:
            if xmlid in loaded_xmlids:
                continue

            Model = self.env.get(model)
            if Model is None:
                continue

            keep = False
            for inheriting in (self.env[m] for m in Model._inherits_children):
                if inheriting._abstract:
                    continue

                parent_field = inheriting._inherits[model]
                children = inheriting.with_context(active_test=False).search(  # noqa: E8507  inheriting varies
                    [(parent_field, "=", res_id)]
                )
                children_xids = {
                    xid
                    for xids in (children and children._get_external_ids().values())
                    for xid in xids
                }
                if children_xids & loaded_xmlids:
                    keep = True
                    break
            if keep:
                _debug.logic(
                    "process_end.kept", xmlid=xmlid, reason="inheriting_child_loaded"
                )
                continue

            if xmlids_per_record.get((model, res_id), 1) > 1:
                _debug.logic(
                    "process_end.stale_xmlid", xmlid=xmlid, reason="other_xmlid_remains"
                )
                xmlids_per_record[(model, res_id)] -= 1
                bad_imd_ids.append(id)
                continue

            if model == "ir.model.constraint":
                cons = Model.browse(res_id)
                target = self.env.get(cons.model.model) if cons.exists() else None
                if target is not None and cons.name in target._table_objects:
                    _debug.logic(
                        "process_end.kept", xmlid=xmlid, reason="constraint_declared"
                    )
                    continue

            _logger.info("Deleting %s@%s (%s)", res_id, model, xmlid)
            record = Model.browse(res_id)
            if record.exists():
                module = xmlid.split(".", 1)[0]
                record = record.with_context(module=module)
                _debug.lifecycle("process_end.record_deleted", xmlid=xmlid, model=model)
                self._process_end_unlink_record(record)
            else:
                _debug.logic(
                    "process_end.stale_xmlid", xmlid=xmlid, reason="record_missing"
                )
                xmlids_per_record[(model, res_id)] = (
                    xmlids_per_record.get((model, res_id), 1) - 1
                )
                bad_imd_ids.append(id)
        _debug.pipeline("process_end_stale_xmlids", count=len(bad_imd_ids))
        if bad_imd_ids:
            self.browse(bad_imd_ids).unlink()

        self.env["ir.ui.view"]._create_all_specific_views(modules)

        loaded_xmlids.clear()

    @api.model
    def toggle_noupdate(self, model: str, res_id: int) -> None:
        self.env[model].browse(res_id).check_access("write")
        xids = self.search([("model", "=", model), ("res_id", "=", res_id)])
        for noupdate, group in xids.grouped("noupdate").items():
            _debug.lifecycle(
                "toggle_noupdate",
                model=model,
                res_id=res_id,
                count=len(group),
                noupdate=not noupdate,
            )
            group.write({"noupdate": not noupdate})
