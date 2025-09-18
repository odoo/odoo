"""Internal helpers for the search-panel component.

Provides ``_search_panel_field_image``, ``_search_panel_domain_image``,
``_search_panel_global_counters``, ``_search_panel_sanitized_parent_hierarchy``,
and ``_search_panel_selection_range`` — consumed by the public API methods
in ``web_search_panel.py``.
"""

from typing import Any

from odoo import api, models
from odoo.fields import Domain
from odoo.orm._typing import DomainType

from .web_read import lazymapping
from .web_read_group_helpers import AND


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def _search_panel_field_image(
        self, field_name: str, **kwargs: Any
    ) -> dict[int, dict[str, Any]]:
        """Return the values in the image of the provided domain by *field_name*.

        :param field_name: the name of a field (type ``many2one`` or
            ``selection``)
        :param kwargs: Keyword arguments:

            * ``model_domain``: domain whose image is returned
            * ``extra_domain``: extra domain to use when counting records
              associated with field values
            * ``enable_counters``: whether to set the key ``'__count'`` in
              image values
            * ``only_counters``: whether to retrieve information on the
              ``model_domain`` image or only counts based on
              ``model_domain`` and ``extra_domain``. In the later case,
              the counts are set whatever is enable_counters.
            * ``limit``: maximal number of values to fetch
            * ``set_limit``: whether to use the provided limit (if any)
        :return: a dict of the form:
            ::

                {
                    id: { 'id': id, 'display_name': display_name, ('__count': c,) },
                    ...
                }
        """

        enable_counters = kwargs.get("enable_counters")
        only_counters = kwargs.get("only_counters")
        extra_domain = Domain(kwargs.get("extra_domain", []))
        no_extra = extra_domain.is_true()
        model_domain = Domain(kwargs.get("model_domain", []))
        count_domain = model_domain & extra_domain

        limit = kwargs.get("limit")
        set_limit = kwargs.get("set_limit")

        if only_counters:
            return self._search_panel_domain_image(field_name, count_domain, True)

        model_domain_image = self._search_panel_domain_image(
            field_name,
            model_domain,
            enable_counters and no_extra,
            set_limit and limit,
        )
        if enable_counters and not no_extra:
            count_domain_image = self._search_panel_domain_image(
                field_name, count_domain, True
            )
            for id, values in model_domain_image.items():
                element = count_domain_image.get(id)
                values["__count"] = element["__count"] if element else 0

        return model_domain_image

    @api.model
    def _search_panel_domain_image(
        self,
        field_name: str,
        domain: DomainType,
        set_count: bool = False,
        limit: int | bool = False,
    ) -> dict[int, dict[str, Any]]:
        """Return the values in the image of the provided *domain* by *field_name*.

        :param domain: domain whose image is returned
        :param field_name: the name of a field (type many2one or selection)
        :param set_count: whether to set the key '__count' in image values. Default is False.
        :param limit: integer, maximal number of values to fetch. Default is False.
        :return: a dict of the form:
            ::

                {
                    id: { 'id': id, 'display_name': display_name, ('__count': c,) },
                    ...
                }
        """
        field = self._fields[field_name]
        if field.type in ("many2one", "many2many"):

            def group_id_name(value):
                return value

        else:
            # field type is selection: see doc above
            desc = self.fields_get([field_name], ["selection"])[field_name]
            field_name_selection = dict(desc["selection"])

            def group_id_name(value):
                return value, field_name_selection[value]

        domain = AND(
            [
                domain,
                [(field_name, "!=", False)],
            ]
        )
        groups = self.with_context(read_group_expand=True).formatted_read_group(
            domain, [field_name], ["__count"], limit=limit
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
    def _search_panel_global_counters(
        self, values_range: dict[int, dict[str, Any]], parent_name: str
    ) -> None:
        """Transform local counts into global counts (local + children).

        Modify *values_range* in place.  Saves the initial (local) counts
        into an auxiliary dict before they could be changed in the loop.

        :param values_range: dict of the form:
            ::

                {
                    id: { 'id': id, '__count': c, parent_name: parent_id, ... }
                    ...
                }
        :param parent_name: string, indicates which key determines the parent
        """
        local_counters = lazymapping(lambda id: values_range[id]["__count"])

        for id in values_range:
            values = values_range[id]
            # here count is the initial value = local count set on values
            count = local_counters[id]
            if count:
                parent_id = values[parent_name]
                while parent_id:
                    values = values_range[parent_id]
                    # Snapshot the parent's original count into the lazy cache
                    # *before* mutating values["__count"] below.  Without this,
                    # a later iteration that walks the same ancestor chain would
                    # read the already-incremented count and double-count.
                    local_counters[parent_id]
                    values["__count"] += count
                    parent_id = values[parent_name]

    @api.model
    def _search_panel_sanitized_parent_hierarchy(
        self,
        records: list[dict[str, Any]],
        parent_name: str,
        ids: list[int],
    ) -> list[dict[str, Any]]:
        """Filter *records* to a maximal ancestor-closed sublist.

        Ensures the resulting sublist:

        1) is closed for the parent relation
        2) every record in it is an ancestor of a record with id in *ids*
           (if ``ids = records.ids``, that condition is automatically
           satisfied)
        3) it is maximal among other sublists with properties 1 and 2.

        :param list[dict[str, Any]] records: the list of records to filter, the
            records must have the form::

                { 'id': id, parent_name: False or (id, display_name),... }

        :param str parent_name: indicates which key determines the parent
        :param list[int] ids: list of record ids
        :return: the sublist of records with the above properties
        """

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
                known_status = records_to_keep.get(record_id)
                if known_status is not None:
                    # the record and its known ancestors have already been considered
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

        # we keep initial order
        return [rec for rec in records if records_to_keep.get(rec["id"])]

    @api.model
    def _search_panel_selection_range(
        self, field_name: str, **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Return values of a selection field, optionally with record counts.

        :param field_name: the name of a field of type selection
        :param kwargs:

            * model_domain: domain used to determine the field image
              values and counts. Default is an empty list.
            * enable_counters: whether to set the key ``'__count'`` on
              values returned. Default is ``False``.
            * expand: whether to return the full range of values for
              the selection field or only the field image values. Default
              is ``False``.
        :return: a list of dicts of the form
            ::

                { 'id': id, 'display_name': display_name, ('__count': c,) }

            with key ``'__count'`` set if ``enable_counters`` is
            ``True``.
        """

        enable_counters = kwargs.get("enable_counters")
        expand = kwargs.get("expand")

        if enable_counters or not expand:
            domain_image = self._search_panel_field_image(
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
