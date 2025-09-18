"""Web CRUD operations on the base model.

Provides ``web_read``, ``web_save``, ``web_search_read``, ``web_name_search``,
and ``web_resequence`` — the fundamental data-access methods consumed by the
webclient's relational model layer.
"""

from collections import defaultdict
from typing import Any

from odoo import api, models
from odoo.api import NewId
from odoo.exceptions import AccessError
from odoo.orm._typing import DomainType
from odoo.tools import OrderedSet


class lazymapping(defaultdict):
    """defaultdict whose factory receives the missing *key* as argument."""

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
        """Search by name and return records formatted per *specification*."""
        id_name_pairs = self.name_search(name, domain, operator, limit)
        if len(specification) == 1 and "display_name" in specification:
            # Batch-browse all IDs so singletons share one prefetch group,
            # reducing N isolated field reads to 1 batched SQL query.
            records = self.with_context(formatted_display_name=True).browse(
                [id for id, _ in id_name_pairs]
            )
            formatted_map = {rec.id: rec.display_name for rec in records}
            return [
                {
                    "id": id,
                    "display_name": name,
                    "__formatted_display_name": formatted_map[id],
                }
                for id, name in id_name_pairs
            ]
        records = self.browse([id for id, _ in id_name_pairs])
        return records.web_read(specification)

    @api.model
    @api.readonly
    def web_search_read(
        self,
        domain: DomainType,
        specification: dict[str, dict],
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
        count_limit: int | None = None,
    ) -> dict[str, int | list]:
        """Search records and return them formatted per *specification*."""
        # Build the search query once — domain processing + access rules.
        # We retain the query to reuse its FROM/WHERE for the count,
        # avoiding the overhead of a second _search() call.
        query = self._search(
            domain, offset=offset, limit=limit, order=order or self._order
        )
        if query.is_empty():
            if not self.env.su:
                self._determine_fields_to_fetch(specification.keys())
            return {"length": 0, "records": []}

        fields_to_fetch = self._determine_fields_to_fetch(specification.keys())
        records = self._fetch_query(query, fields_to_fetch)
        values_records = records.web_read(specification)
        return self._format_web_search_read_results(
            domain,
            values_records,
            offset,
            limit,
            count_limit,
            _query=query,
        )

    def _format_web_search_read_results(
        self,
        domain: DomainType,
        records: list[dict],
        offset: int = 0,
        limit: int | None = None,
        count_limit: int | None = None,
        _query: Any = None,
    ) -> dict[str, int | list]:
        """Wrap *records* with a length estimate for pager support."""
        if not records:
            return {
                "length": 0,
                "records": [],
            }
        current_length = len(records) + offset
        limit_reached = len(records) == limit
        force_search_count = self.env.context.get("force_search_count")
        count_limit_reached = count_limit and count_limit <= current_length
        if limit and (
            (limit_reached and not count_limit_reached) or force_search_count
        ):
            if _query is not None:
                # Reuse the data query's FROM/WHERE — same joins, same
                # filters — instead of rebuilding via search_count().
                length = _query.count_matching(count_limit)
            else:
                length = self.search_count(domain, limit=count_limit)
        else:
            length = current_length
        return {
            "length": length,
            "records": records,
        }

    def web_save(
        self, vals, specification: dict[str, dict], next_id=None
    ) -> list[dict]:
        """Create or write a record and return it formatted per *specification*."""
        if self:
            self.write(vals)
            record = self
        else:
            record = self.create(vals)
        if next_id:
            record = self.browse(next_id)
        return record.with_context(bin_size=True).web_read(specification)

    def web_save_multi(
        self, vals_list: list[dict], specification: dict[str, dict]
    ) -> list[dict]:
        """Write multiple records at once and return them formatted.

        Groups records with identical vals dicts and issues a single
        ``write()`` per group, amortising access-check, ``modified()``,
        and validation overhead.  Records with unhashable vals (x2many
        commands) fall back to individual writes.
        """
        if len(self) != len(vals_list):
            msg = "Each record must have a corresponding vals entry."
            raise ValueError(msg)

        # Group records sharing identical vals — one write() per group
        # instead of one per record.  Preserves prefetch set via
        # with_prefetch() so reads inside write() stay batched.
        groups: dict[frozenset, list[int]] = {}
        vals_by_key: dict[frozenset, dict] = {}
        for record, vals in zip(self, vals_list, strict=True):
            try:
                key = frozenset(vals.items())
            except TypeError:
                # Unhashable values (x2many commands) — write individually
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
    def web_read(self, specification: dict[str, dict]) -> list[dict]:
        """Read records and recursively resolve sub-specifications.

        This is the main entry point used by the webclient to fetch record
        data.  It handles many2one, x2many, reference, many2one_reference,
        and properties fields by recursively calling ``web_read`` on
        co-records according to *specification*.
        """
        fields_to_read = list(specification) or ["id"]

        if set(fields_to_read) == {"id"}:
            # if we request to read only the ids, we have them already so we can build the return dictionaries immediately
            # this also avoid a call to read on the co-model that might have different access rules
            values_list = [{"id": id_} for id_ in self._ids]
        else:
            values_list: list[dict] = self.read(fields_to_read, load=None)

        if not values_list:
            return values_list

        def cleanup(vals: dict) -> dict:
            """Fixup vals['id'] of a new record."""
            if not vals["id"]:
                vals["id"] = vals["id"].origin or False
            return vals

        for field_name, field_spec in specification.items():
            field = self._fields.get(field_name)
            if field is None:
                continue

            if field.type == "many2one":
                if "fields" not in field_spec:
                    for values in values_list:
                        if isinstance(values[field_name], NewId):
                            values[field_name] = values[field_name].origin
                    continue

                # Normalize NewId → origin before sub-spec processing;
                # NewId.__bool__ is False so they'd be excluded from co_ids
                # but the `is False` guard below wouldn't catch them → KeyError.
                for values in values_list:
                    if isinstance(values[field_name], NewId):
                        values[field_name] = values[field_name].origin or False

                # Extract co-record IDs directly from already-fetched values
                # instead of re-traversing the cache via self[field_name].
                co_ids = OrderedSet(
                    vals[field_name] for vals in values_list if vals[field_name]
                )
                co_records = self.env[field.comodel_name].browse(co_ids)
                if "context" in field_spec:
                    co_records = co_records.with_context(**field_spec["context"])

                extra_fields = dict(field_spec["fields"])
                extra_fields.pop("display_name", None)

                many2one_data = {
                    vals["id"]: cleanup(vals)
                    for vals in co_records.web_read(extra_fields)
                }

                if "display_name" in field_spec["fields"]:
                    for rec in co_records.sudo():
                        many2one_data[rec.id]["display_name"] = rec.display_name

                for values in values_list:
                    if values[field_name] is False:
                        continue
                    vals = many2one_data[values[field_name]]
                    values[field_name] = vals["id"] and vals

            elif field.type in ("one2many", "many2many"):
                if not field_spec:
                    continue

                # Extract co-record IDs directly from already-fetched values
                # instead of re-traversing the cache via self[field_name].
                co_ids = OrderedSet(
                    id_ for vals in values_list for id_ in vals[field_name]
                )
                co_records = self.env[field.comodel_name].browse(co_ids)

                if field_spec.get("order"):
                    # Include the field's context when reapplying to preserve settings like active_test=False
                    field_context = field.context or {}
                    co_records = (
                        co_records.with_context(active_test=False)
                        .search(
                            [("id", "in", co_records.ids)],
                            order=field_spec["order"],
                        )
                        .with_context(**co_records.env.context, **field_context)
                    )
                    order_key = {
                        co_record.id: index
                        for index, co_record in enumerate(co_records)
                    }
                    for values in values_list:
                        # filter out inaccessible corecords in case of "cache pollution"
                        values[field_name] = [
                            id_ for id_ in values[field_name] if id_ in order_key
                        ]
                        values[field_name] = sorted(
                            values[field_name], key=order_key.__getitem__
                        )

                if "context" in field_spec:
                    co_records = co_records.with_context(**field_spec["context"])

                if "fields" in field_spec:
                    if field_spec.get("limit") is not None:
                        limit = field_spec["limit"]
                        ids_to_read = OrderedSet(
                            id_
                            for values in values_list
                            for id_ in values[field_name][:limit]
                        )
                        co_records = co_records.browse(ids_to_read)

                    x2many_data = {
                        vals["id"]: vals
                        for vals in co_records.web_read(field_spec["fields"])
                    }

                    for values in values_list:
                        values[field_name] = [
                            x2many_data.get(id_, {"id": id_})
                            for id_ in values[field_name]
                        ]

            elif field.type in ("reference", "many2one_reference"):
                if not field_spec:
                    continue

                values_by_id = {vals["id"]: vals for vals in values_list}
                has_sub_fields = "fields" in field_spec
                # Non-trivial sub-fields let us infer existence from
                # web_read results (id-only spec short-circuits without
                # hitting the DB, so it cannot detect deleted records).
                can_infer_existence = has_sub_fields and any(
                    fname != "id" for fname in field_spec["fields"]
                )

                # --- First pass: collect co-records grouped by model ---
                # Field values are already in cache from the earlier
                # self.read(), so record[field_name] is free.
                co_by_model = defaultdict(list)  # model → [(record_id, co_id)]
                for record in self:
                    if not record[field_name]:
                        continue
                    if field.type == "reference":
                        co_rec = record[field_name]
                        co_by_model[co_rec._name].append((record.id, co_rec.id))
                    else:  # many2one_reference
                        if not record[field.model_field]:
                            values_by_id[record.id][field_name] = False
                            continue
                        co_by_model[record[field.model_field]].append(
                            (record.id, record[field_name])
                        )

                # --- Batch web_read / exists() per model ---
                for model_name, pairs in co_by_model.items():
                    co_ids = list({co_id for _, co_id in pairs})
                    CoModel = self.env[model_name]
                    if "context" in field_spec:
                        CoModel = CoModel.with_context(**field_spec["context"])
                    co_recordset = CoModel.browse(co_ids)

                    co_data = {}
                    if has_sub_fields:
                        try:
                            co_data = {
                                d["id"]: d
                                for d in co_recordset.web_read(field_spec["fields"])
                            }
                        except AccessError:
                            # Per-record fallback: some records may be accessible
                            for co_id in co_ids:
                                try:
                                    result = CoModel.browse(co_id).web_read(
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
                        set(co_data)
                        if can_infer_existence
                        else set(co_recordset.exists().ids)
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

            elif field.type == "properties":
                if not field_spec or "fields" not in field_spec:
                    continue

                prop_ctx = field_spec.get("context")

                # --- Collect all property co-record IDs for batching ---
                # Key: (comodel, property_name) → set of co-record IDs
                batch_ids: dict[tuple[str, str], set[int]] = defaultdict(set)
                batch_specs: dict[str, dict] = {}  # property_name → spec['fields']

                for values in values_list:
                    for property_name, spec in field_spec["fields"].items():
                        if "fields" not in spec:
                            continue
                        prop = next(
                            (
                                p
                                for p in values[field_name]
                                if p.get("name") == property_name
                            ),
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

                # --- Batch web_read per (comodel, property_name) ---
                co_data: dict[tuple[str, str], dict[int, dict]] = {}
                for (comodel, prop_name), ids in batch_ids.items():
                    co_records = (
                        self.env[comodel].with_context(**(prop_ctx or {})).browse(ids)
                    )
                    co_data[(comodel, prop_name)] = {
                        d["id"]: d for d in co_records.web_read(batch_specs[prop_name])
                    }

                # --- Distribute results ---
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
                                    # Original returns web_read() list format
                                    prop["value"] = [data[co_id]]
                            elif prop.get("type") == "many2many":
                                prop["value"] = [
                                    data.get(r[0], r) for r in prop["value"]
                                ]

                        next_values.append(prop)

                    values[field_name] = next_values

        return values_list

    def web_resequence(
        self,
        specification: dict[str, dict],
        field_name: str = "sequence",
        offset: int = 0,
    ) -> list[dict]:
        """Re-sequences a number of records in the model, by their ids.

        The re-sequencing starts at the first record of ``ids``, the
        sequence number starts at ``offset`` and is incremented by one
        after each record.

        The returning value is a read of the resequenced records with
        the specification given in the parameter.

        :param specification: specification for the read of the
            resequenced records
        :param field_name: field used for sequence specification,
            defaults to ``"sequence"``
        :param offset: sequence number for first record in ``ids``,
            allows starting the resequencing from an arbitrary number,
            defaults to ``0``
        """
        if field_name not in self._fields:
            return []
        if not self:
            return []

        field = self._fields[field_name]

        # Access checks — once for all records instead of once per write()
        self.check_access("write")
        self._check_field_access(field, "write")

        # Set log-access fields once on the full recordset
        if self._log_access:
            self._fields["write_uid"].mark_dirty(self, self.env.uid)
            self._fields["write_date"].mark_dirty(self, self.env.cr.now())

        # Mark each record's sequence value as dirty (cache-only, no SQL yet)
        for i, record in enumerate(self, start=offset):
            field.mark_dirty(record, i)

        # Trigger recomputation of dependent fields — once for all records
        self.modified([field_name])

        # Validate constraints — once for all records
        self._validate_fields([field_name])

        if self._check_company_auto:
            self._check_company([field_name])

        return self.web_read(specification)
