from collections import defaultdict
from typing import Any

from odoo import api, models
from odoo.api import DomainType, NewId
from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.fields import Datetime as FieldsDatetime
from odoo.tools import OrderedSet
from odoo.tools.authority_keys import strip_authority_keys
from odoo.tools.cache_version import versioned, versioned_envelope


class lazymapping(defaultdict):
    def __missing__(self, key: Any) -> Any:
        value = self.default_factory(key)
        self[key] = value
        return value


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    @api.readonly
    def web_name_search(
        self,
        name: str,
        specification: dict[str, dict],
        domain: DomainType | None = None,
        operator: str = "ilike",
        limit: int = 100,
    ) -> list[dict]:
        id_name_pairs = self.name_search(name, domain, operator, limit)
        if len(specification) == 1 and "display_name" in specification:
            records = (
                self.with_context(formatted_display_name=True)
                .browse([id for id, _ in id_name_pairs])
                .exists()
            )
            formatted_map = {rec.id: rec.display_name for rec in records}
            return [
                {
                    "id": id,
                    "display_name": name,
                    "__formatted_display_name": formatted_map.get(id, name),
                }
                for id, name in id_name_pairs
            ]
        records = self.browse([id for id, _ in id_name_pairs])
        return records.web_read(specification)

    @api.model
    @api.readonly
    @versioned
    def web_search_read(
        self,
        domain: DomainType,
        specification: dict[str, dict],
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
        count_limit: int | None = None,
    ) -> dict[str, int | list]:
        specification = self._screen_fields_spec(specification)
        records = self.search_fetch(
            domain, list(specification), offset=offset, limit=limit, order=order
        )
        values_records = records.web_read(specification) if records else []
        return self._format_web_search_read_results(
            domain, values_records, offset, limit, count_limit
        )

    def _format_web_search_read_results(
        self,
        domain: DomainType,
        records: list[dict],
        offset: int = 0,
        limit: int | None = None,
        count_limit: int | None = None,
    ) -> dict[str, int | list]:
        if not records:
            if not offset:
                return {"length": 0, "records": []}
            return {
                "length": self.search_count(domain, limit=count_limit),
                "records": [],
            }
        current_length = len(records) + offset
        limit_reached = len(records) == limit
        force_search_count = self.env.context.get("force_search_count")
        count_limit_reached = count_limit and count_limit <= current_length
        if limit and (
            (limit_reached and not count_limit_reached) or force_search_count
        ):
            length = self.search_count(domain, limit=count_limit)
        else:
            length = current_length
        return {
            "length": length,
            "records": records,
        }

    def web_save(
        self,
        vals,
        specification: dict[str, dict],
        next_id=None,
        last_write_date=None,
        known_values=None,
    ) -> list[dict]:
        self._check_web_save_vals(vals)
        if self:
            if known_values is not None:
                is_multi = known_values and all(
                    str(k).lstrip("-").isdigit() for k in known_values
                )
                if known_values and not is_multi:
                    self._check_concurrent_field_changes(vals, known_values)
                else:
                    self._check_concurrent_field_changes_multi(vals, known_values)
            elif last_write_date and "write_date" in self._fields:
                self.check_singleton()
                self.env.cr.execute(
                    'SELECT write_date FROM "%s" WHERE id = %%s' % self._table,
                    (self.id,),
                )
                row = self.env.cr.fetchone()
                server_write_date = row[0] if row else None
                client_dt = FieldsDatetime.to_datetime(last_write_date)
                if server_write_date and getattr(server_write_date, "tzinfo", None):
                    server_write_date = server_write_date.replace(tzinfo=None)
                if server_write_date:
                    server_write_date = server_write_date.replace(microsecond=0)
                if client_dt:
                    client_dt = client_dt.replace(microsecond=0)
                if server_write_date and client_dt and server_write_date > client_dt:
                    raise UserError(
                        self.env._(
                            "This record was modified by another user.\n"
                            "Please reload and re-apply your changes."
                        )
                    )
            self.write(vals)
            record = self
        else:
            record = self.create(vals)
        if next_id:
            record = self.browse(next_id)
        return record.with_context(bin_size=True).web_read(specification)

    _X2M_ROW_ID_COMMANDS = (
        Command.UPDATE,
        Command.DELETE,
        Command.UNLINK,
        Command.LINK,
    )

    def _check_web_save_vals(self, vals: dict) -> None:
        unknown = [name for name in vals if name not in self._fields]
        if unknown:
            raise UserError(
                self.env._(
                    "This form is out of date and references field(s) that no "
                    "longer exist (%s). Your changes were not saved — please "
                    "reload the page and re-apply them.",
                    ", ".join(unknown),
                )
            )
        for name, value in vals.items():
            field = self._fields[name]
            if field.type not in ("one2many", "many2many") or not isinstance(
                value, (list, tuple)
            ):
                continue
            for command in value:
                if not isinstance(command, (list, tuple)) or len(command) < 2:
                    continue
                if command[0] in self._X2M_ROW_ID_COMMANDS:
                    row_ids = (command[1],)
                elif (
                    command[0] == Command.SET
                    and len(command) > 2
                    and isinstance(command[2], (list, tuple))
                ):
                    row_ids = command[2]
                else:
                    continue
                for row_id in row_ids:
                    if not isinstance(row_id, int) or isinstance(row_id, bool):
                        raise UserError(
                            self.env._(
                                "Invalid record reference '%(row_id)s' in field \""
                                '%(field)s". Your changes were not saved — '
                                "please reload the page and re-apply them.",
                                row_id=row_id,
                                field=field.string or name,
                            )
                        )

    _CONCURRENCY_SAFE_TYPES = frozenset(
        (
            "integer",
            "boolean",
            "char",
            "text",
            "selection",
            "float",
            "monetary",
            "many2one",
        )
    )

    def _get_fields_concurrency_checkable(self, vals):
        return [
            n
            for n in vals
            if n in self._fields
            and self._fields[n].store
            and self._fields[n].column_type
            and self._fields[n].column_type[0] != "jsonb"
            and self._fields[n].type in self._CONCURRENCY_SAFE_TYPES
        ]

    def _is_field_modified_concurrently(self, name, server_raw, baseline_raw, new_raw):
        try:
            field = self._fields[name]
            if field.type == "many2one" and server_raw:
                co_record = self.env[field.comodel_name].browse(server_raw)
                if not co_record.with_context(active_test=False)._filtered_access(
                    "read"
                ):
                    return False
            current = self._coerce_concurrency_value(field, server_raw)
            baseline = self._coerce_concurrency_value(field, baseline_raw)
            new = self._coerce_concurrency_value(field, new_raw)
            return current not in (baseline, new)
        # fmt: skip below: ruff format (target-version=py314) rewrites the
        except (TypeError, ValueError):  # fmt: skip
            return False

    def _check_concurrent_field_changes(self, vals, known_values):
        self.check_singleton()
        names = [
            n for n in self._get_fields_concurrency_checkable(vals) if n in known_values
        ]
        if not names:
            return
        cols = ", ".join('"%s"' % n for n in names)
        self.env.cr.execute(
            'SELECT %s FROM "%s" WHERE id = %%s' % (cols, self._table),
            (self.id,),
        )
        row = self.env.cr.fetchone()
        if not row:
            return
        conflicts = [
            self._fields[name].string or name
            for name, server_raw in zip(names, row, strict=True)
            if self._is_field_modified_concurrently(
                name, server_raw, known_values[name], vals[name]
            )
        ]
        if conflicts:
            raise UserError(
                self.env._(
                    "This record was modified by another user while you were "
                    "editing it.\nConflicting field(s): %s.\n"
                    "Please reload and re-apply your changes.",
                    ", ".join(conflicts),
                )
            )

    def _check_concurrent_field_changes_multi(self, vals, known_values):
        self._check_concurrent_field_changes_records(
            dict.fromkeys(self.ids, vals), known_values
        )

    def _check_concurrent_field_changes_multi_list(self, vals_list, known_values):
        self._check_concurrent_field_changes_records(
            dict(zip(self.ids, vals_list, strict=True)), known_values
        )

    def _check_concurrent_field_changes_records(self, vals_by_id, known_values):
        if not vals_by_id:
            return
        all_keys = set().union(*(v.keys() for v in vals_by_id.values()))
        checkable = self._get_fields_concurrency_checkable(dict.fromkeys(all_keys))
        if not checkable:
            return
        baselines = {}
        for rec_id, base in known_values.items():
            try:
                baselines[int(rec_id)] = base
            except TypeError, ValueError:
                continue
        cols = ", ".join('"%s"' % n for n in checkable)
        self.env.cr.execute(
            'SELECT id, %s FROM "%s" WHERE id = ANY(%%s)' % (cols, self._table),
            (list(self.ids),),
        )
        current = {
            row[0]: dict(zip(checkable, row[1:], strict=True))
            for row in self.env.cr.fetchall()
        }
        conflict_ids = set()
        conflict_fields = set()
        for rec_id, server_row in current.items():
            baseline = baselines.get(rec_id)
            vals = vals_by_id.get(rec_id)
            if not baseline or not vals:
                continue
            for name in checkable:
                if name not in baseline or name not in vals:
                    continue
                if self._is_field_modified_concurrently(
                    name, server_row[name], baseline[name], vals[name]
                ):
                    conflict_ids.add(rec_id)
                    conflict_fields.add(self._fields[name].string or name)
        if conflict_ids:
            raise UserError(
                self.env._(
                    "%(count)s of the records you edited were modified by another "
                    "user in the meantime.\nConflicting field(s): %(fields)s.\n"
                    "Please reload and re-apply your changes.",
                    count=len(conflict_ids),
                    fields=", ".join(sorted(conflict_fields)),
                )
            )

    @staticmethod
    def _coerce_concurrency_value(field, value):
        ftype = field.type
        if value is None or value is False:
            return {
                "integer": 0,
                "float": 0.0,
                "monetary": 0.0,
                "boolean": False,
                "many2one": False,
            }.get(ftype, "")
        if ftype == "many2one":
            if isinstance(value, dict):
                return value.get("id") or False
            if isinstance(value, (list, tuple)):
                return value[0] if value else False
            return int(value) if isinstance(value, (int, float)) else False
        if ftype == "integer":
            return int(value)
        if ftype in ("float", "monetary"):
            return round(float(value), 6)
        if ftype == "boolean":
            return bool(value)
        if isinstance(value, (dict, list, tuple, set, frozenset, bytes, bytearray)):
            raise TypeError(
                f"{ftype} concurrency baseline has uncomparable type "
                f"{type(value).__name__}"
            )
        return str(value)

    def web_save_multi(
        self,
        vals_list: list[dict],
        specification: dict[str, dict],
        known_values=None,
    ) -> list[dict]:
        if len(self) != len(vals_list):
            raise UserError(
                self.env._("Each record must have a corresponding vals entry.")
            )

        for vals in vals_list:
            self._check_web_save_vals(vals)

        if known_values is not None:
            self._check_concurrent_field_changes_multi_list(vals_list, known_values)

        groups: dict[frozenset, list[int]] = {}
        vals_by_key: dict[frozenset, dict] = {}
        for record, vals in zip(self, vals_list, strict=True):
            try:
                key = frozenset(vals.items())
            except TypeError:
                record.write(vals)
                continue
            if key not in groups:
                groups[key] = []
                vals_by_key[key] = vals
            groups[key].append(record.id)

        prefetch_ids = self._prefetch_ids
        for key, ids in groups.items():
            self.browse(ids).with_prefetch(prefetch_ids).write(vals_by_key[key])

        return self.with_context(bin_size=True).web_read(specification)

    @api.readonly
    @versioned_envelope
    def web_read(self, specification: dict[str, dict]) -> list[dict]:
        if not self:
            return []
        if set(specification) <= {"id"}:
            self.check_access("read")
        return self._web_read(specification)

    def _web_read(self, specification: dict[str, dict]) -> list[dict]:
        fields_to_read = list(specification) or ["id"]

        if set(fields_to_read) == {"id"}:
            values_list = [
                {"id": (id_.origin or False) if isinstance(id_, NewId) else id_}
                for id_ in self._ids
            ]
        else:
            values_list: list[dict] = self.read(fields_to_read, load=None)

        if not values_list:
            return values_list

        for field_name, field_spec in specification.items():
            field = self._fields.get(field_name)
            if field is None:
                continue

            if field.type == "many2one":
                self._web_read_resolve_many2one(
                    values_list, field, field_name, field_spec
                )
            elif field.type in ("one2many", "many2many"):
                self._web_read_resolve_x2many(
                    values_list, field, field_name, field_spec
                )
            elif field.type in ("reference", "many2one_reference"):
                self._web_read_resolve_reference(
                    values_list, field, field_name, field_spec
                )
            elif field.type == "properties":
                self._web_read_resolve_properties(values_list, field_name, field_spec)

        return values_list

    def _web_read_resolve_many2one(self, values_list, field, field_name, field_spec):
        def cleanup(vals: dict) -> dict:
            if not vals["id"]:
                vals["id"] = vals["id"].origin or False
            return vals

        if "fields" not in field_spec:
            for values in values_list:
                if isinstance(values[field_name], NewId):
                    values[field_name] = values[field_name].origin or False
            return

        for values in values_list:
            if isinstance(values[field_name], NewId):
                values[field_name] = values[field_name].origin or False

        co_ids = OrderedSet(
            vals[field_name] for vals in values_list if vals[field_name]
        )
        co_records = self.env[field.comodel_name].browse(co_ids)
        if "context" in field_spec:
            co_records = co_records.with_context(
                **strip_authority_keys(field_spec["context"], door="web_read")
            )

        extra_fields = dict(field_spec["fields"])
        extra_fields.pop("display_name", None)

        if co_records:
            readable_records = (
                co_records.with_context(active_test=False)
                ._filtered_access("read")
                .with_context(co_records.env.context)
            )
        else:
            readable_records = co_records

        many2one_data = {
            vals["id"]: cleanup(vals)
            for vals in readable_records._web_read(extra_fields)
        }

        withheld = co_records.browse(
            [co_id for co_id in co_ids if co_id not in many2one_data]
        )
        for rec in withheld.sudo().exists():
            many2one_data[rec.id] = {"id": rec.id}

        if "display_name" in field_spec["fields"]:
            named = co_records.browse([co_id for co_id in many2one_data if co_id])
            for rec in named._filtered_display_name_access().sudo():
                many2one_data[rec.id]["display_name"] = rec.display_name

        for values in values_list:
            if values[field_name] is False:
                continue
            vals = many2one_data.get(values[field_name])
            values[field_name] = (vals and vals["id"] and vals) or False

    def _web_read_resolve_x2many(self, values_list, field, field_name, field_spec):
        if not field_spec:
            return

        co_ids = OrderedSet(id_ for vals in values_list for id_ in vals[field_name])
        co_records = self.env[field.comodel_name].browse(co_ids)

        if field_spec.get("order"):
            field_context = field.context or {}
            if not (co_records and co_records.browse().has_access("read")):
                co_records = co_records.browse()
            else:
                try:
                    co_records = (
                        co_records.with_context(active_test=False)
                        .search(
                            [("id", "in", co_records.ids)],
                            order=field_spec["order"],
                        )
                        .with_context(co_records.env.context, **field_context)
                    )
                except AccessError, UserError, ValueError:
                    co_records = co_records.browse()
            order_key = {
                co_record.id: index for index, co_record in enumerate(co_records)
            }
            for values in values_list:
                values[field_name] = [
                    id_ for id_ in values[field_name] if id_ in order_key
                ]
                values[field_name] = sorted(
                    values[field_name], key=order_key.__getitem__
                )
        elif "fields" in field_spec:
            if co_records and co_records.browse().has_access("read"):
                accessible = co_records.with_context(
                    active_test=False
                )._filtered_access("read")
                accessible_ids = set(accessible.ids)
                for values in values_list:
                    values[field_name] = [
                        id_ for id_ in values[field_name] if id_ in accessible_ids
                    ]
                co_records = accessible.with_context(co_records.env.context)

        if "context" in field_spec:
            co_records = co_records.with_context(
                **strip_authority_keys(field_spec["context"], door="web_read")
            )

        if "fields" in field_spec:
            if field_spec.get("limit") is not None:
                limit = field_spec["limit"]
                ids_to_read = OrderedSet(
                    id_ for values in values_list for id_ in values[field_name][:limit]
                )
                co_records = co_records.browse(ids_to_read)

            x2many_data = {
                vals["id"]: vals for vals in co_records._web_read(field_spec["fields"])
            }

            for values in values_list:
                values[field_name] = [
                    x2many_data.get(id_, {"id": id_}) for id_ in values[field_name]
                ]

    def _web_read_resolve_reference(self, values_list, field, field_name, field_spec):
        if not field_spec:
            return

        values_by_id = {vals["id"]: vals for vals in values_list}
        has_sub_fields = "fields" in field_spec
        can_infer_existence = has_sub_fields and any(
            fname != "id" for fname in field_spec["fields"]
        )

        co_by_model = defaultdict(list)
        for record in self:
            if record.id not in values_by_id:
                continue
            if not record[field_name]:
                continue
            if field.type == "reference":
                co_rec = record[field_name]
                co_by_model[co_rec._name].append((record.id, co_rec.id))
            else:
                if not record[field.model_field]:
                    values_by_id[record.id][field_name] = False
                    continue
                co_by_model[record[field.model_field]].append(
                    (record.id, record[field_name])
                )

        for model_name, pairs in co_by_model.items():
            co_ids = list({co_id for _, co_id in pairs})
            CoModel = self.env[model_name]
            if "context" in field_spec:
                CoModel = CoModel.with_context(
                    **strip_authority_keys(field_spec["context"], door="web_read")
                )
            co_recordset = CoModel.browse(co_ids)

            co_data = {}
            if has_sub_fields:
                try:
                    co_data = {
                        d["id"]: d for d in co_recordset._web_read(field_spec["fields"])
                    }
                except AccessError:
                    for co_id in co_ids:
                        try:
                            result = CoModel.browse(co_id)._web_read(
                                field_spec["fields"]
                            )
                            if result:
                                co_data[co_id] = result[0]
                        except AccessError:
                            co_data[co_id] = {
                                "id": co_id,
                                "display_name": self.env._(
                                    "You don't have access to this record"
                                ),
                            }

            existing_ids = (
                set(co_data) if can_infer_existence else set(co_recordset.exists().ids)
            )

            for record_id, co_id in pairs:
                record_values = values_by_id[record_id]
                if co_id not in existing_ids:
                    record_values[field_name] = False
                    if field.type == "many2one_reference":
                        record_values[field.model_field] = False
                    continue
                if has_sub_fields and co_id in co_data:
                    record_values[field_name] = co_data[co_id]
                    if field.type == "reference":
                        record_values[field_name]["id"] = {
                            "id": co_id,
                            "model": model_name,
                        }

    def _web_read_resolve_properties(self, values_list, field_name, field_spec):
        if not field_spec or "fields" not in field_spec:
            return

        prop_ctx = strip_authority_keys(field_spec.get("context"), door="web_read")

        batch_ids: dict[tuple[str, str], set[int]] = defaultdict(set)
        batch_specs: dict[str, dict] = {}

        for values in values_list:
            for property_name, spec in field_spec["fields"].items():
                if "fields" not in spec:
                    continue
                prop = next(
                    (p for p in values[field_name] if p.get("name") == property_name),
                    None,
                )
                if not prop or not prop.get("comodel") or not prop.get("value"):
                    continue
                comodel = prop["comodel"]
                batch_specs[property_name] = spec["fields"]
                if prop.get("type") == "many2one":
                    batch_ids[(comodel, property_name)].add(prop["value"][0])
                elif prop.get("type") == "many2many":
                    batch_ids[(comodel, property_name)].update(
                        r[0] for r in prop["value"]
                    )

        co_data: dict[tuple[str, str], dict[int, dict]] = {}
        for (comodel, prop_name), ids in batch_ids.items():
            co_records = self.env[comodel].with_context(**(prop_ctx or {})).browse(ids)
            co_data[(comodel, prop_name)] = {
                d["id"]: d for d in co_records._web_read(batch_specs[prop_name])
            }

        for values in values_list:
            old_values = values[field_name]
            next_values = []
            for property_name, spec in field_spec["fields"].items():
                prop = next(
                    (p for p in old_values if p.get("name") == property_name),
                    None,
                )
                if not prop:
                    continue

                comodel = prop.get("comodel")
                if comodel and prop.get("value") and "fields" in spec:
                    data = co_data.get((comodel, property_name), {})
                    if prop.get("type") == "many2one":
                        co_id = prop["value"][0]
                        if co_id in data:
                            prop["value"] = [data[co_id]]
                    elif prop.get("type") == "many2many":
                        prop["value"] = [data.get(r[0], r) for r in prop["value"]]

                next_values.append(prop)

            values[field_name] = next_values

    def web_resequence(
        self,
        specification: dict[str, dict],
        field_name: str = "sequence",
        offset: int = 0,
    ) -> list[dict]:
        if field_name not in self._fields:
            return []
        if not self:
            return []

        field = self._fields[field_name]

        fast_path = (
            type(self).write is models.BaseModel.write
            and field.store
            and field.type == "integer"
            and not field.compute
            and not field.inverse
        )

        if not fast_path:
            for i, record in enumerate(self, start=offset):
                record.write({field_name: i})
            return self.web_read(specification)

        self.check_access("write")
        self._check_field_access(field, "write")

        if self._log_access:
            self._fields["write_uid"].mark_dirty(self, self.env.uid)
            self._fields["write_date"].mark_dirty(self, self.env.cr.now())

        for i, record in enumerate(self, start=offset):
            field.mark_dirty(record, i)

        self.modified([field_name])

        self._check_fields([field_name])

        if self._check_company_auto:
            self._check_company([field_name])

        return self.web_read(specification)
