from typing import Any

from odoo import api, models
from odoo.api import DomainType
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

from .web_read import lazymapping
from .web_read_group_helpers import AND

_log = DebugLog(__name__)


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def _search_panel_get_field_image(
        self, field_name: str, **kwargs: Any
    ) -> dict[int, dict[str, Any]]:
        enable_counters = kwargs.get("enable_counters")
        only_counters = kwargs.get("only_counters")
        extra_domain = Domain(kwargs.get("extra_domain", []))
        no_extra = extra_domain.is_true()
        model_domain = Domain(kwargs.get("model_domain", []))
        count_domain = model_domain & extra_domain

        limit = kwargs.get("limit")
        set_limit = kwargs.get("set_limit")

        if only_counters:
            return self._search_panel_get_domain_image(field_name, count_domain, True)

        model_domain_image = self._search_panel_get_domain_image(
            field_name,
            model_domain,
            enable_counters and no_extra,
            set_limit and limit,
        )
        if enable_counters and not no_extra:
            count_domain_image = self._search_panel_get_domain_image(
                field_name, count_domain, True
            )
            for id, values in model_domain_image.items():
                element = count_domain_image.get(id)
                values["__count"] = element["__count"] if element else 0

        return model_domain_image

    @api.model
    def _search_panel_get_domain_image(
        self,
        field_name: str,
        domain: DomainType,
        set_count: bool = False,
        limit: int | bool = False,
    ) -> dict[int, dict[str, Any]]:
        field = self._fields[field_name]
        if field.type in ("many2one", "many2many"):

            def group_id_name(value):
                return value

        else:
            desc = self.fields_get([field_name], ["selection"])[field_name]
            field_name_selection = dict(desc["selection"])

            def group_id_name(value):
                return value, field_name_selection.get(value, value)

        domain = AND(
            [
                domain,
                [(field_name, "!=", False)],
            ]
        )
        groups = self.with_context(read_group_expand=True).formatted_read_group(
            domain,
            [field_name],
            ["__count"],
            limit=limit or None,
        )

        domain_image = {}
        for group in groups:
            id_, display_name = group_id_name(group[field_name])
            values = {
                "id": id_,
                "display_name": display_name,
            }
            if set_count:
                values["__count"] = group["__count"]
            domain_image[id_] = values

        return domain_image

    @api.model
    def _search_panel_rollup_counters_global(
        self, values_range: dict[int, dict[str, Any]], parent_name: str
    ) -> None:
        local_counters = lazymapping(lambda id: values_range[id]["__count"])

        for id, values in values_range.items():
            count = local_counters[id]
            if count:
                parent_id = values[parent_name]
                while parent_id:
                    values = values_range[parent_id]
                    local_counters[parent_id]
                    values["__count"] += count
                    parent_id = values[parent_name]

    @api.model
    def _search_panel_filter_parent_hierarchy(
        self,
        records: list[dict[str, Any]],
        parent_name: str,
        ids: list[int],
    ) -> list[dict[str, Any]]:
        def get_parent_id(record):
            value = record[parent_name]
            return value and value[0]

        allowed_records = {record["id"]: record for record in records}
        records_to_keep = {}
        for id in ids:
            record_id = id
            ancestor_chain = {}
            chain_is_fully_included = True
            while chain_is_fully_included and record_id:
                if record_id in ancestor_chain:
                    # Repair only the response graph: do not mutate stored data or
                    # the caller's records. One broken edge makes the cycle a tree.
                    record = allowed_records[record_id]
                    allowed_records[record_id] = {**record, parent_name: False}
                    _log.logic(
                        "parent-cycle", record_id=record_id, parent_name=parent_name
                    )
                    break
                known_status = records_to_keep.get(record_id)
                if known_status is not None:
                    chain_is_fully_included = known_status
                    break
                record = allowed_records.get(record_id)
                if record:
                    ancestor_chain[record_id] = record
                    record_id = get_parent_id(record)
                else:
                    chain_is_fully_included = False

            for r_id in ancestor_chain:
                records_to_keep[r_id] = chain_is_fully_included

        return [
            allowed_records[rec["id"]]
            for rec in records
            if records_to_keep.get(rec["id"])
        ]

    @api.model
    def _search_panel_get_selection_range(
        self, field_name: str, **kwargs: Any
    ) -> list[dict[str, Any]]:
        enable_counters = kwargs.get("enable_counters")
        expand = kwargs.get("expand")

        if enable_counters or not expand:
            domain_image = self._search_panel_get_field_image(
                field_name, only_counters=expand, **kwargs
            )

        if not expand:
            return list(domain_image.values())

        selection = self.fields_get([field_name])[field_name]["selection"]

        selection_range = []
        for value, label in selection:
            values = {
                "id": value,
                "display_name": label,
            }
            if enable_counters:
                image_element = domain_image.get(value)
                values["__count"] = image_element["__count"] if image_element else 0
            selection_range.append(values)

        return selection_range
