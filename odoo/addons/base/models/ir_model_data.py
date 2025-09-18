import logging
import random
import typing
from collections import defaultdict
from itertools import batched
from operator import itemgetter
from typing import Any, Self

import psycopg

from odoo import api, fields, models, tools
from odoo.exceptions import AccessError, MissingError
from odoo.orm.registration import add_field
from odoo.tools import OrderedSet, groupby, reset_cached_properties, unique
from odoo.tools.translate import _
from odoo.orm._typing import ValuesType

from .ir_model import MODULE_UNINSTALL_FLAG

_logger = logging.getLogger(__name__)


class IrModelData(models.Model):
    """Holds external identifier keys for records in the database.
    This has two main uses:

        * allows easy data integration with third-party systems,
          making import/export/sync of data possible, as records
          can be uniquely identified across multiple systems
        * allows tracking the origin of data installed by Odoo
          modules themselves, thus making it possible to later
          update them seamlessly.
    """

    _name = "ir.model.data"
    _description = "Model Data"
    _order = "module, model, name"
    _allow_sudo_commands = False

    name = fields.Char(
        string="External Identifier",
        required=True,
        help="External Key/Identifier that can be used for data integration with third-party systems",
    )
    complete_name = fields.Char(compute="_compute_complete_name", string="Complete ID")
    model = fields.Char(string="Model Name", required=True)
    module = fields.Char(default="", required=True)
    res_id = fields.Many2oneReference(
        string="Record ID",
        help="ID of the target record in the database",
        model_field="model",
    )
    noupdate = fields.Boolean(string="Non Updatable", default=False)
    reference = fields.Char(
        string="Reference",
        compute="_compute_reference",
        readonly=True,
        store=False,
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
                    xid.display_name = xid.complete_name

    # NEW V8 API
    @api.model
    @tools.ormcache("xmlid")
    def _xmlid_lookup(self, xmlid: str) -> tuple[str, int]:
        """Low level xmlid lookup
        Return (res_model, res_id) or raise ValueError if not found
        """
        module, name = xmlid.split(".", 1)
        query = "SELECT model, res_id FROM ir_model_data WHERE module=%s AND name=%s"
        self.env.cr.execute(query, [module, name])
        result = self.env.cr.fetchone()
        if not (result and result[1]):
            raise ValueError(f"External ID not found in the system: {xmlid}")
        return result

    @api.model
    def _xmlid_to_res_model_res_id(
        self, xmlid: str, raise_if_not_found: bool = False
    ) -> tuple[str, int] | tuple[typing.Literal[False], typing.Literal[False]]:
        """Return (res_model, res_id)"""
        try:
            return self._xmlid_lookup(xmlid)
        except ValueError:
            if raise_if_not_found:
                raise
            return (False, False)

    @api.model
    def _xmlid_to_res_id(
        self, xmlid: str, raise_if_not_found: bool = False
    ) -> int | bool:
        """Returns res_id"""
        return self._xmlid_to_res_model_res_id(xmlid, raise_if_not_found)[1]

    @api.model
    def check_object_reference(
        self, module: str, xml_id: str, raise_on_access_error: bool = False
    ) -> tuple[str, int | bool]:
        """Returns (model, res_id) corresponding to a given module and xml_id (cached), if and only if the user has the necessary access rights
        to see that object, otherwise raise a ValueError if raise_on_access_error is True or returns a tuple (model found, False)
        """
        model, res_id = self._xmlid_lookup(f"{module}.{xml_id}")
        # search on id found in result to check if current user has read access right
        if self.env[model].search([("id", "=", res_id)]):
            return model, res_id
        if raise_on_access_error:
            raise AccessError(
                _(
                    'Not enough access rights on the external ID "%(module)s.%(xml_id)s"',
                    module=module,
                    xml_id=xml_id,
                )
            )
        return model, False

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        vals_list = super().copy_data(default=default)
        for model, vals in zip(self, vals_list, strict=True):
            rand = f"{random.getrandbits(16):04x}"
            vals["name"] = f"{model.name}_{rand}"
        return vals_list

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        res = super().create(vals_list)
        if any(vals.get("model") == "res.groups" for vals in vals_list):
            self.env.registry.clear_cache("groups")
        return res

    def write(self, vals: dict[str, Any]) -> bool:
        self.env.registry.clear_cache()  # _xmlid_lookup
        res = super().write(vals)
        if vals.get("model") == "res.groups":
            self.env.registry.clear_cache("groups")
        return res

    def unlink(self) -> bool:
        """Regular unlink method, but make sure to clear the caches."""
        self.env.registry.clear_cache()  # _xmlid_lookup
        if self and any(data.model == "res.groups" for data in self.exists()):
            self.env.registry.clear_cache("groups")
        return super().unlink()

    def _lookup_xmlids(self, xml_ids: list[str], model: Any) -> list[tuple]:
        """Look up the given XML ids of the given model."""
        if not xml_ids:
            return []

        # group xml_ids by prefix
        bymodule = defaultdict(set)
        for xml_id in xml_ids:
            prefix, suffix = xml_id.split(".", 1)
            bymodule[prefix].add(suffix)

        # query xml_ids by prefix
        result = []
        cr = self.env.cr
        for prefix, suffixes in bymodule.items():
            query = f"""
                SELECT d.id, d.module, d.name, d.model, d.res_id, d.noupdate, r.id
                FROM ir_model_data d LEFT JOIN "{model._table}" r on d.res_id=r.id
                WHERE d.module=%s AND d.name = ANY(%s)
            """
            for subsuffixes in batched(suffixes, cr.BATCH_SIZE, strict=False):
                cr.execute(query, (prefix, list(subsuffixes)))
                result.extend(cr.fetchall())

        return result

    @api.model
    def _update_xmlids(
        self, data_list: list[dict[str, Any]], update: bool = False
    ) -> None:
        """Create or update the given XML ids.

        :param data_list: list of dicts with keys `xml_id` (XMLID to
            assign), `noupdate` (flag on XMLID), `record` (target record).
        :param update: should be ``True`` when upgrading a module
        """
        if not data_list:
            return

        rows = OrderedSet()
        for data in data_list:
            prefix, suffix = data["xml_id"].split(".", 1)
            record = data["record"]
            noupdate = bool(data.get("noupdate"))
            rows.add((prefix, suffix, record._name, record.id, noupdate))

        for sub_rows in batched(rows, self.env.cr.BATCH_SIZE, strict=False):
            # insert rows or update them
            query = self._build_update_xmlids_query(sub_rows, update)
            try:
                self.env.cr.execute(query, [arg for row in sub_rows for arg in row])
                result = self.env.cr.fetchall()
                if result:
                    for (
                        module,
                        name,
                        model,
                        res_id,
                        create_date,
                        write_date,
                    ) in result:
                        # small optimisation: during install a lot of xmlid are created/updated.
                        # Instead of clearing the cache, set the correct value in the cache to avoid a bunch of query
                        self._xmlid_lookup.__cache__.add_value(
                            self,
                            f"{module}.{name}",
                            cache_value=(model, res_id),
                        )
                        if create_date != write_date:
                            # something was updated, notify other workers
                            # it is possible that create_date and write_date
                            # have the same value after an update if it was
                            # created in the same transaction, no need to invalidate other worker cache
                            # cache in this case.
                            self.env.registry.cache_invalidated.add("default")

            except Exception:
                _logger.error(
                    "Failed to insert ir_model_data\n%s",
                    "\n".join(str(row) for row in sub_rows),
                )
                raise

        # update loaded_xmlids
        self.pool.loaded_xmlids.update(f"{row[0]}.{row[1]}" for row in rows)

        if any(row[2] == "res.groups" for row in rows):
            self.env.registry.clear_cache("groups")

    # NOTE: this method is overridden in web_studio; if you need to make another
    #  override, make sure it is compatible with the one that is there.
    def _build_insert_xmlids_values(self) -> dict[str, str]:
        return {
            "module": "%s",
            "name": "%s",
            "model": "%s",
            "res_id": "%s",
            "noupdate": "%s",
        }

    def _build_update_xmlids_query(self, sub_rows: list[tuple], update: bool) -> str:
        rows = self._build_insert_xmlids_values()
        row_names = f"({','.join(rows.keys())})"
        row_placeholders = f"({','.join(rows.values())})"
        row_placeholders = ", ".join([row_placeholders] * len(sub_rows))
        return """
            INSERT INTO ir_model_data {row_names}
            VALUES {row_placeholder}
            ON CONFLICT (module, name)
            DO UPDATE SET (model, res_id, write_date) =
                (EXCLUDED.model, EXCLUDED.res_id, now() at time zone 'UTC')
                WHERE (ir_model_data.res_id != EXCLUDED.res_id OR ir_model_data.model != EXCLUDED.model) {and_where}
            RETURNING module, name, model, res_id, create_date, write_date
        """.format(
            row_names=row_names,
            row_placeholder=row_placeholders,
            and_where="AND NOT ir_model_data.noupdate" if update else "",
        )

    @api.model
    def _load_xmlid(self, xml_id: str) -> Any:
        """Simply mark the given XML id as being loaded, and return the
        corresponding record.
        """
        record = self.env.ref(xml_id, raise_if_not_found=False)
        if record:
            self.pool.loaded_xmlids.add(xml_id)
        return record

    @api.model
    def _module_data_uninstall(self, modules_to_remove: list[str]) -> None:
        """Deletes all the records referenced by the ir.model.data entries
        ``ids`` along with their corresponding database backed (including
        dropping tables, columns, FKs, etc, as long as there is no other
        ir.model.data entry holding a reference to them (which indicates that
        they are still owned by another module).
        Attempts to perform the deletion in an appropriate order to maximize
        the chance of gracefully deleting all records.
        This step is performed as part of the full uninstallation of a module.
        """
        if not self.env.is_system():
            raise AccessError(
                _("Administrator access is required to uninstall a module")
            )

        # enable model/field deletion
        # we deactivate prefetching to not try to read a column that has been deleted
        self = self.with_context(
            **{MODULE_UNINSTALL_FLAG: True, "prefetch_fields": False}
        )

        # determine records to unlink
        records_items = []  # [(model, id)]
        model_ids = []
        field_ids = []
        selection_ids = []
        constraint_ids = []

        module_data = self.search(
            [("module", "in", modules_to_remove)], order="id DESC"
        )
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

        # avoid prefetching fields that are going to be deleted: during uninstall, it is
        # possible to perform a recompute (via flush) after the database columns have been
        # deleted but before the new registry has been created, meaning the recompute will
        # be executed on a stale registry, and if some of the data for executing the compute
        # methods is not in cache it will be fetched, and fields that exist in the registry but not
        # in the database will be prefetched, this will of course fail and prevent the uninstall.
        has_shared_field = False
        for ir_field in self.env["ir.model.fields"].browse(field_ids):
            model = self.pool.get(ir_field.model)
            if model is not None:
                field = model._fields.get(ir_field.name)
                if field is not None and field.prefetch:
                    if field._toplevel:
                        # the field is specific to this registry
                        field.prefetch = False
                    else:
                        # the field is shared across registries; don't modify it
                        Field = type(field)
                        field_ = Field(_base_fields__=(field, Field(prefetch=False)))
                        add_field(
                            self.env.registry[ir_field.model],
                            ir_field.name,
                            field_,
                        )
                        field_.setup(model)
                        has_shared_field = True
        if has_shared_field:
            reset_cached_properties(self.env.registry)

        # to collect external ids of records that cannot be deleted
        undeletable_ids = []

        def delete(records):
            # do not delete records that have other external ids (and thus do
            # not belong to the modules being installed)
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
            if not records:
                return

            # special case for ir.model.fields
            if records._name == "ir.model.fields":
                missing = records - records.exists()
                if missing:
                    # delete orphan external ids right now;
                    # an orphan ir.model.data can happen if the ir.model.field is deleted via
                    # an ONDELETE CASCADE, in which case we must verify that the records we're
                    # processing exist in the database otherwise a MissingError will be raised
                    orphans = ref_data.filtered(lambda r: r.res_id in missing._ids)
                    _logger.info("Deleting orphan ir_model_data %s", orphans)
                    orphans.unlink()
                    # /!\ this must go before any field accesses on `records`
                    records -= missing
                # do not remove LOG_ACCESS_COLUMNS unless _log_access is False
                # on the model
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

            # now delete the records
            _logger.info("Deleting %s", records)
            try:
                with self.env.cr.savepoint():
                    cloc_exclude_data.unlink()
                    records.unlink()
            except Exception:
                if len(records) <= 1:
                    undeletable_ids.extend(ref_data._ids)
                else:
                    # divide the batch in two, and recursively delete them
                    half_size = len(records) // 2
                    delete(records[:half_size])
                    delete(records[half_size:])

        # remove non-model records first, grouped by batches of the same model
        for model, items in groupby(unique(records_items), itemgetter(0)):
            ids = [item[1] for item in items]
            # we cannot guarantee that the ir.model.data points to an existing model
            if model in self.env:
                delete(self.env[model].browse(ids))
            else:
                _logger.info(
                    "Orphan ir.model.data records %s refer to unavailable model '%s'",
                    ids,
                    model,
                )

        # Remove copied views. This must happen after removing all records from
        # the modules to remove, otherwise ondelete='restrict' may prevent the
        # deletion of some view. This must also happen before cleaning up the
        # database schema, otherwise some dependent fields may no longer exist
        # in database.
        modules = self.env["ir.module.module"].search(
            [("name", "in", modules_to_remove)]
        )
        modules._remove_copied_views()

        # remove constraints
        delete(self.env["ir.model.constraint"].browse(unique(constraint_ids)))

        # If we delete a selection field, and some of its values have ondelete='cascade',
        # we expect the records with that value to be deleted. If we delete the field first,
        # the column is dropped and the selection is gone, and thus the records above will not
        # be deleted.
        delete(
            self.env["ir.model.fields.selection"].browse(unique(selection_ids)).exists()
        )
        delete(self.env["ir.model.fields"].browse(unique(field_ids)))
        relations = self.env["ir.model.relation"].search(
            [("module", "in", modules.ids)]
        )
        relations._module_data_uninstall()

        # remove models
        delete(self.env["ir.model"].browse(unique(model_ids)))

        # log undeletable ids
        _logger.info("ir.model.data could not be deleted (%s)", undeletable_ids)

        # sort out which undeletable model data may have become deletable again because
        # of records being cascade-deleted or tables being dropped just above
        for data in self.browse(undeletable_ids).exists():
            if data.model not in self.env.registry:
                continue
            record = self.env[data.model].browse(data.res_id)
            try:
                with self.env.cr.savepoint():
                    if record.exists():
                        # record exists therefore the data is still undeletable,
                        # remove it from module_data
                        module_data -= data
                        continue
            except psycopg.ProgrammingError:
                # This most likely means that the record does not exist, since record.exists()
                # is rougly equivalent to `SELECT id FROM table WHERE id=record.id` and it may raise
                # a ProgrammingError because the table no longer exists (and so does the
                # record), also applies to ir.model.fields, constraints, etc.
                pass
        # remove remaining module data records
        module_data.unlink()

    @api.model
    def _process_end_unlink_record(self, record: Any) -> None:
        record.unlink()

    @api.model
    def _process_end(self, modules: list[str]) -> None:
        """Clear records removed from updated module data.
        This method is called at the end of the module loading process.
        It is meant to removed records that are no longer present in the
        updated data. Such records are recognised as the one with an xml id
        and a module in ir_model_data and noupdate set to false, but not
        present in self.pool.loaded_xmlids.
        """
        if not modules or tools.config.get("import_partial"):
            return

        bad_imd_ids = []
        self = self.with_context({MODULE_UNINSTALL_FLAG: True})
        loaded_xmlids = self.pool.loaded_xmlids

        query = """ SELECT id, module || '.' || name, model, res_id FROM ir_model_data
                    WHERE module = ANY(%s) AND res_id IS NOT NULL AND COALESCE(noupdate, false) != %s ORDER BY id DESC
                """
        self.env.cr.execute(query, (list(modules), True))
        for id, xmlid, model, res_id in self.env.cr.fetchall():
            if xmlid in loaded_xmlids:
                continue

            Model = self.env.get(model)
            if Model is None:
                continue

            # when _inherits parents are implicitly created we give them an
            # external id (if their descendant has one) in order to e.g.
            # properly remove them when the module is deleted, however this
            # generated id is *not* provided during update yet we don't want to
            # try and remove either the xid or the record, so check if the
            # record has a child we've just updated
            keep = False
            for inheriting in (self.env[m] for m in Model._inherits_children):
                # ignore mixins
                if inheriting._abstract:
                    continue

                parent_field = inheriting._inherits[model]
                children = inheriting.with_context(active_test=False).search(
                    [(parent_field, "=", res_id)]
                )
                children_xids = {
                    xid
                    for xids in (children and children._get_external_ids().values())
                    for xid in xids
                }
                if children_xids & loaded_xmlids:
                    # at least one child was loaded
                    keep = True
                    break
            if keep:
                continue

            # if the record has other associated xids, only remove the xid
            if self.search_count(
                [
                    ("model", "=", model),
                    ("res_id", "=", res_id),
                    ("id", "!=", id),
                    ("id", "not in", bad_imd_ids),
                ]
            ):
                bad_imd_ids.append(id)
                continue

            _logger.info("Deleting %s@%s (%s)", res_id, model, xmlid)
            record = Model.browse(res_id)
            if record.exists():
                module = xmlid.split(".", 1)[0]
                record = record.with_context(module=module)
                self._process_end_unlink_record(record)
            else:
                bad_imd_ids.append(id)
        if bad_imd_ids:
            self.browse(bad_imd_ids).unlink()

        # Once all views are created create specific ones
        self.env["ir.ui.view"]._create_all_specific_views(modules)

        loaded_xmlids.clear()
        return

    @api.model
    def toggle_noupdate(self, model: str, res_id: int) -> None:
        """Toggle the noupdate flag on the external id of the record"""
        self.env[model].browse(res_id).check_access("write")
        for xid in self.search([("model", "=", model), ("res_id", "=", res_id)]):
            xid.noupdate = not xid.noupdate
