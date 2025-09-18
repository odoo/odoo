"""Web read-group, grouping, and aggregation operations on the base model.

Provides ``web_read_group``, ``formatted_read_group``,
``formatted_read_grouping_sets``, and ``read_progress_bar`` — the grouped-data
methods used by list, kanban, pivot, and graph views.

Temporal expansion, group filling, and field-type formatters live in
``web_read_group_helpers.py``.
"""

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from odoo import api, models
from odoo.fields import Domain
from odoo.models import BaseModel, regex_order
from odoo.orm._typing import DomainType
from odoo.tools import unique

from .web_read_group_helpers import AND

MAX_NUMBER_OPENED_GROUPS = 10


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    @api.readonly
    def web_read_group(
        self,
        domain: DomainType,
        groupby: list[str] | tuple[str, ...],
        aggregates: Sequence[str] = (),
        limit: int | None = None,
        offset: int = 0,
        order: str | None = None,
        *,
        auto_unfold: bool = False,
        opening_info: list[dict] | None = None,
        unfold_read_specification: dict[str, dict] | None = None,
        unfold_read_default_limit: (
            int | None
        ) = 80,  # Limit of record by unfolded group by default
        groupby_read_specification: dict[str, dict] | None = None,
    ) -> dict[str, int | list]:
        """
        Serves as the primary method for loading grouped data in list and kanban views.

        This method wraps :meth:`~.formatted_read_group` to return both the grouped
        data and the total number of groups matching the search domain. It also
        conditionally opens (unfolds) groups based on the `auto_unfold` parameter
        and the `__fold` key returned by :meth:`~.formatted_read_group`.

        A group is considered "open" if it contains a `__records` or `__groups` key.
        - `__records`: The result of a :meth:`~.web_search_read` call for the group.
        - `__groups`: The results of subgroupings.

        :param domain: :ref:`A search domain <reference/orm/domains>`.
        :param groupby: A list of groupby specification at each level, see :meth:`~.formatted_read_group`.
        :param aggregates: A list of aggregate specifications. see :meth:`~.formatted_read_group`
        :param limit: The maximum number of top-level groups to return. see :meth:`~.formatted_read_group`
        :param offset: The offset for the top-level groups. see :meth:`~.formatted_read_group`
        :param order: A sort string, as used in :meth:`~.search`
        :param auto_unfold: If `True`, automatically unfolds the first 10 groups according to their
            `__fold` key, if present; otherwise, it is unfolded by default.
            This is typically `True` for kanban views and `False` for list views.
        :param opening_info: The state of currently opened groups, used for reloading.
          ::

            opening_info = [{
                "value": raw_value_groupby,
                "folded": True or False,
                ["offset": int,]  # present if unfolded
                ["limit": int,]  # present if unfolded
                ["progressbar_domain": progressbar_domain,]  # present if unfolded, e.g., when clicking on a progress bar section
                ["groups": <opening_info>,]  # present if unfolded
            }]

        :param unfold_read_specification: The read specification for :meth:`~.web_read` when unfolding a group.
        :param unfold_read_default_limit: The default record limit to apply when unfolding a group.
        :param groupby_read_specification: The :meth:`~.web_read` specification for reading the records
            that are being grouped on. This is mainly for list views with <groupby> leaves.
            {<groupby_spec>: <read_specification>}

        :return: A dictionary with the following structure:
          ::

            {
                'groups': <groups>,
                'length': <total_group_count>,
            }

            Where <groups> is the result of :meth:`~.formatted_read_group`, but with an
            added `__groups` key for subgroups or a `__records` key for the result of :meth:`~.web_read`
            for records within the group.

        """
        if not isinstance(groupby, (list, tuple)) or not groupby:
            msg = "groupby must be a non-empty list or tuple"
            raise ValueError(msg)

        aggregates = list(aggregates)
        if "__count" not in aggregates:  # Used for computing length of sublevel groups
            aggregates.append("__count")
        domain = Domain(domain).optimize(self)

        # dict to help creating order compatible with _read_group and for search
        dict_order: dict[str, str] = {}  # {fname_and_property: "<direction> <nulls>"}
        for order_part in order.split(",") if order else ():
            order_match = regex_order.match(order_part)
            if not order_match:
                raise ValueError(f"Invalid order {order!r} for web_read_group()")
            fname_and_property = order_match["field"]
            if order_match["property"]:
                fname_and_property = f"{fname_and_property}.{order_match['property']}"
            direction = (order_match["direction"] or "ASC").upper()
            if order_match["nulls"]:
                direction = f"{direction} {order_match['nulls'].upper()}"
            dict_order[fname_and_property] = direction

        # First level of grouping
        first_groupby = [groupby[0]]
        read_group_order = self._get_read_group_order(
            dict_order, first_groupby, aggregates
        )
        groups, length = self._formatted_read_group_with_length(
            domain,
            first_groupby,
            aggregates,
            offset=offset,
            limit=limit,
            order=read_group_order,
        )

        # Open sublevel of grouping (list) and get all subgroup to open into records.
        # [{limit: int, offset: int, domain: domain, group: <group>}]
        records_opening_info: list[dict[str, Any]] = []

        self._open_groups(
            records_opening_info=records_opening_info,
            groups=groups,
            domain=domain,
            groupby=groupby,
            aggregates=aggregates,
            dict_order=dict_order,
            auto_unfold=auto_unfold,
            opening_info=opening_info,
            unfold_read_default_limit=unfold_read_default_limit,
            parent_opening_info=opening_info,
            parent_group_domain=Domain.TRUE,
        )

        # Open last level of grouping, meaning read records of groups
        if records_opening_info:
            order_specs = [
                f"{fname} {direction}"
                for fname, direction in dict_order.items()
                # Remove order that are already unique for each group,
                # that may avoid a left join and simplify the order (not apply if granularity)
                if fname not in groupby
                if fname != "__count"
            ]
            for order_str in self._order.split(","):
                fname = order_str.strip().split(" ", 1)[0]
                if fname not in dict_order and fname not in groupby:
                    order_specs.append(order_str)

            order_searches = ", ".join(order_specs)
            recordset_groups = [
                (
                    self.search(
                        domain & sub_search["domain"],
                        order=order_searches,
                        limit=sub_search["limit"],
                        offset=sub_search["offset"],
                    )
                    if sub_search["group"]["__count"]
                    else self.browse()
                )
                for sub_search in records_opening_info
            ]

            all_records = self.browse().union(*recordset_groups)
            record_mapped = dict(
                zip(
                    all_records._ids,
                    all_records.web_read(unfold_read_specification or {}),
                    strict=True,
                )
            )

            for opening, records in zip(
                records_opening_info, recordset_groups, strict=True
            ):
                opening["group"]["__records"] = [
                    record_mapped[record_id] for record_id in records._ids
                ]

        # Read additional info of grouped field record and add it to specific groups
        self._add_groupby_values(groupby_read_specification, groupby, groups)

        return {
            "groups": groups,
            "length": length,
        }

    def _formatted_read_group_with_length(
        self, domain, groupby, aggregates, offset=0, limit=None, order=None
    ):
        """Return ``(groups, total_length)`` for paginated group results."""
        groups = self.formatted_read_group(
            domain, groupby, aggregates, offset=offset, limit=limit, order=order
        )

        if not groups:
            length = 0
        elif limit and len(groups) == limit:
            length = limit + len(
                self._read_group(
                    domain,
                    groupby=groupby,
                    offset=limit,
                )
            )
        else:
            length = len(groups) + offset

        return groups, length

    def _add_groupby_values(
        self,
        groupby_read_specification: dict[str, dict] | None,
        groupby: list[str],
        current_groups: list,
    ):
        """Enrich groups with extra ``web_read`` data for the grouped field."""
        if (
            not groupby_read_specification
            or groupby_read_specification.keys().isdisjoint(groupby)
        ):
            return

        for groupby_spec in groupby:
            if groupby_spec in groupby_read_specification:
                relational_field = self._fields[groupby_spec]
                if not relational_field.comodel_name:
                    msg = "Groupby read specification requires a relational field"
                    raise ValueError(msg)
                group_ids = [
                    id_label[0]
                    for group in current_groups
                    if (id_label := group[groupby_spec])
                ]
                records = self.env[relational_field.comodel_name].browse(group_ids)

                result_read = records.web_read(groupby_read_specification[groupby_spec])
                result_read_map = dict(zip(records._ids, result_read, strict=True))
                for group in current_groups:
                    id_label = group[groupby_spec]
                    group["__values"] = (
                        result_read_map[id_label[0]] if id_label else {"id": False}
                    )

            current_groups = [
                subgroup
                for group in current_groups
                for subgroup in group.get("__groups", {}).get("groups", ())
            ]

    def _get_read_group_order(
        self,
        dict_order: dict[str, str],
        groupby: list[str],
        aggregates: Sequence[str],
    ) -> str:
        """Build an order string compatible with ``_read_group``."""
        if not dict_order:
            return ", ".join(groupby)

        groupby = list(groupby)
        order_spec = []
        for fname, direction in dict_order.items():
            if fname == "__count":
                order_spec.append(f"{fname} {direction}")
                continue
            for group in list(groupby):
                if fname == group or group.startswith(f"{fname}:"):
                    groupby.remove(group)
                    order_spec.append(f"{group} {direction}")
                    break
            for agg_spec in aggregates:
                if agg_spec.startswith(f"{fname}:"):
                    order_spec.append(f"{agg_spec} {direction}")
                    break

        return ", ".join(order_spec + groupby)

    def _open_groups(
        self,
        *,
        records_opening_info: list[dict[str, Any]],
        groups: list[dict],
        domain: Domain,
        groupby: list[str],
        aggregates: list[str],
        dict_order: dict[str, str],
        auto_unfold: bool,
        opening_info: list[dict] | None,
        unfold_read_default_limit: int | None,
        parent_opening_info: list[dict] | None,
        parent_group_domain: Domain,
    ):
        """Recursively open (unfold) groups into sub-groups or records."""
        max_number_opened_group = (
            self.env.context.get("max_number_opened_groups") or MAX_NUMBER_OPENED_GROUPS
        )

        parent_opening_info_dict = {
            info_opening["value"]: info_opening
            for info_opening in parent_opening_info or ()
        }
        groupby_spec = groupby[0]
        field = self._fields[groupby_spec.split(":")[0].split(".")[0]]
        nb_opened_group = 0

        last_level = len(groupby) == 1
        if not last_level:
            read_group_order = self._get_read_group_order(
                dict_order, [groupby[1]], aggregates
            )

        for group in groups:
            # Remove __fold information, no need for the webclient,
            # the groups is unfold if __groups/__records exists
            fold_info = "__fold" in group
            fold = group.pop("__fold", False)

            groupby_value = group[groupby_spec]
            # For relational/date/datetime/property tags field
            raw_groupby_value = (
                groupby_value[0] if isinstance(groupby_value, tuple) else groupby_value
            )

            limit = unfold_read_default_limit
            offset = 0
            progressbar_domain = subgroup_opening_info = None
            if opening_info and raw_groupby_value in parent_opening_info_dict:
                group_info = parent_opening_info_dict[raw_groupby_value]
                if group_info["folded"]:
                    continue
                limit = group_info["limit"]
                offset = group_info["offset"]
                progressbar_domain = group_info.get("progressbar_domain")
                subgroup_opening_info = group_info.get("groups")

            elif (
                # Auto Fold/unfold
                (not auto_unfold and not fold_info)
                or nb_opened_group >= max_number_opened_group
                or fold
                # Empty recordset is folded by default
                or (field.relational and not group[groupby_spec])
            ):
                continue

            # => Open group
            nb_opened_group += 1
            if last_level:  # Open records
                records_domain = parent_group_domain & Domain(group["__extra_domain"])

                # when we click on a part of the progress bar, we force a domain
                # for a specific open column/group, we want to keep this for the next reload
                if progressbar_domain:
                    records_domain &= Domain(progressbar_domain)

                # TODO also for groups ?
                # Simulate the same behavior than in relational_model.js
                # If the offset is bigger than the number of record (a record has been deleted)
                # reset the offset to 0 and add the information to the group to update the webclient too
                if offset and offset >= group["__count"]:
                    group["__offset"] = offset = 0

                records_opening_info.append(
                    {
                        "domain": records_domain,
                        "limit": limit,
                        "offset": offset,
                        "group": group,
                    }
                )

            else:  # Open subgroups
                subgroup_domain = parent_group_domain
                if group["__extra_domain"]:
                    subgroup_domain &= Domain(group["__extra_domain"])
                # That's not optimal but hard to batch because of limit/offset.
                # Moreover it isn't critical since it is when user opens group manually, then
                # the number of it should be small.
                subgroups, length = self._formatted_read_group_with_length(
                    domain=(subgroup_domain & domain),
                    groupby=[groupby[1]],
                    aggregates=aggregates,
                    offset=offset,
                    limit=limit,
                    order=read_group_order,
                )

                group["__groups"] = {
                    "groups": subgroups,
                    "length": length,
                }
                self._open_groups(
                    records_opening_info=records_opening_info,
                    groups=subgroups,
                    domain=domain,
                    groupby=groupby[1:],
                    aggregates=aggregates,
                    dict_order=dict_order,
                    auto_unfold=False,
                    opening_info=opening_info,
                    unfold_read_default_limit=unfold_read_default_limit,
                    parent_opening_info=subgroup_opening_info,
                    parent_group_domain=subgroup_domain,
                )

    @api.model
    @api.readonly
    def formatted_read_grouping_sets(
        self,
        domain: DomainType,
        grouping_sets: Sequence[Sequence[str]],
        aggregates: Sequence[str] = (),
        *,
        order: str | None = None,
    ):
        """
        A method similar to :meth:`_read_grouping_set` but with all the
        formatting needed by the webclient.
        It is a multi groupby version of formatted_read_group allowing to have
        aggregates for different groupby specifications in a single SQL requests.

        :param domain: :ref:`A search domain <reference/orm/domains>`.
            Use an empty list to match all records.
        :param grouping_sets: list of list of groupby descriptions by which the
            records will be grouped.

            A groupby description is either a field (then it will be
            grouped by that field) or a string
            ``'<field>:<granularity>'``.

            Right now, the only supported granularities are:

            * ``day``
            * ``week``
            * ``month``
            * ``quarter``
            * ``year``

            and they only make sense for date/datetime fields.

            Additionally integer date parts are also supported:

            * ``year_number``
            * ``quarter_number``
            * ``month_number``
            * ``iso_week_number``
            * ``day_of_year``
            * ``day_of_month``
            * ``day_of_week``
            * ``hour_number``
            * ``minute_number``
            * ``second_number``

        :param aggregates: list of aggregates specification. Each
            element is ``'<field>:<agg>'`` (aggregate field with
            aggregation function ``agg``). The possible aggregation
            functions are the ones provided by
            `PostgreSQL <https://www.postgresql.org/docs/current/static/functions-aggregate.html>`_,
            except ``count_distinct`` and ``array_agg_distinct`` with
            the expected meaning.

        :param order: optional ``order by`` specification, for
            overriding the natural sort ordering of the groups, see
            :meth:`~.search`.

        :return: list of list of dict such as
            ``[[{'groupy_spec': value, ...}, ...], ...]`` containing:

            * the groupby values: ``{groupby[i]: <value>}``
            * the aggregate values: ``{aggregates[i]: <value>}``
            * ``'__extra_domain'``: list of tuples specifying the group
              search criteria
            * ``'__fold'``: boolean if a fold_name is set on the comodel
              and read_group_expand is activated

        :raise AccessError: if user is not allowed to access requested
            information
        """
        grouping_sets = [tuple(groupby) for groupby in grouping_sets]
        aggregates = tuple(
            agg.replace(":recordset", ":array_agg") for agg in aggregates
        )

        if not order:
            order = ", ".join(
                unique(spec for groupby in grouping_sets for spec in groupby)
            )

        groups_list = self._read_grouping_sets(
            domain,
            grouping_sets,
            aggregates,
            order=order,
        )

        for groups_index, groupby in enumerate(grouping_sets):
            if self._web_read_group_field_expand(groupby):
                groups_list[groups_index] = self._web_read_group_expand(
                    domain,
                    groups_list[groups_index],
                    groupby[0],
                    aggregates,
                    order,
                )

        for groups_index, groupby in enumerate(grouping_sets):
            fill_temporal = self.env.context.get("fill_temporal")
            if groupby and (fill_temporal or isinstance(fill_temporal, dict)):
                if not isinstance(fill_temporal, dict):
                    fill_temporal = {}
                # This assumes that existing data is sorted by field 'groupby_name'
                groups_list[groups_index] = self._web_read_group_fill_temporal(
                    groups_list[groups_index],
                    groupby,
                    aggregates,
                    **fill_temporal,
                )

        return [
            self._web_read_group_format(groupby, aggregates, groups)
            for groupby, groups in zip(grouping_sets, groups_list, strict=True)
        ]

    @api.model
    @api.readonly
    def formatted_read_group(
        self,
        domain: DomainType,
        groupby: Sequence[str] = (),
        aggregates: Sequence[str] = (),
        having: DomainType = (),
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
    ) -> list[dict]:
        """
        A method similar to :meth:`_read_group` but with all the
        formatting needed by the webclient.

        :param domain: :ref:`A search domain <reference/orm/domains>`.
            Use an empty list to match all records.
        :param groupby: list of groupby descriptions by which the
            records will be grouped.

            A groupby description is either a field (then it will be
            grouped by that field) or a string
            ``'<field>:<granularity>'``.

            Right now, the only supported granularities are:

            * ``day``
            * ``week``
            * ``month``
            * ``quarter``
            * ``year``

            and they only make sense for date/datetime fields.

            Additionally integer date parts are also supported:

            * ``year_number``
            * ``quarter_number``
            * ``month_number``
            * ``iso_week_number``
            * ``day_of_year``
            * ``day_of_month``
            * ``day_of_week``
            * ``hour_number``
            * ``minute_number``
            * ``second_number``

        :param aggregates: list of aggregates specification. Each
            element is ``'<field>:<agg>'`` (aggregate field with
            aggregation function ``agg``). The possible aggregation
            functions are the ones provided by
            `PostgreSQL <https://www.postgresql.org/docs/current/static/functions-aggregate.html>`_,
            except ``count_distinct`` and ``array_agg_distinct`` with
            the expected meaning.

        :param having: A domain where the valid "fields" are the
            aggregates.

        :param offset: optional number of groups to skip

        :param limit: optional max number of groups to return

        :param order: optional ``order by`` specification, for
            overriding the natural sort ordering of the groups, see
            :meth:`~.search`.

        :return: list of dict such as
            ``[{'groupy_spec': value, ...}, ...]`` containing:

            * the groupby values: ``{groupby[i]: <value>}``
            * the aggregate values: ``{aggregates[i]: <value>}``
            * ``'__extra_domain'``: list of tuples specifying the group
              search criteria
            * ``'__fold'``: boolean if a fold_name is set on the comodel
              and read_group_expand is activated

        :raise AccessError: if user is not allowed to access requested
            information
        """
        groupby = tuple(groupby)
        aggregates = tuple(
            agg.replace(":recordset", ":array_agg") for agg in aggregates
        )

        if not order:
            order = ", ".join(groupby)

        groups = self._read_group(
            domain,
            groupby,
            aggregates,
            having=having,
            offset=offset,
            limit=limit,
            order=order,
        )

        # Note: group_expand is only done if the limit isn't reached and when the offset == 0
        # to avoid inconsistency in the web client pager. Anyway, in practice, this feature should
        # be used only when there are few groups (or without limit for the kanban view).
        if (
            not offset
            and (not limit or len(groups) < limit)
            and self._web_read_group_field_expand(groupby)
        ):
            # It doesn't respect the order with aggregates inside
            expand_groups = self._web_read_group_expand(
                domain, groups, groupby[0], aggregates, order
            )
            if not limit or len(expand_groups) <= limit:
                # Ditch the result of expand_groups because the limit is reached and to avoid
                # returning inconsistent result inside length of web_read_group
                groups = expand_groups

        fill_temporal = self.env.context.get("fill_temporal")
        if groupby and (fill_temporal or isinstance(fill_temporal, dict)):
            if limit or offset:
                msg = "You cannot use fill_temporal with a limit or an offset"
                raise ValueError(msg)
            if not isinstance(fill_temporal, dict):
                fill_temporal = {}
            # This assumes that existing data is sorted by field 'groupby_name'
            groups = self._web_read_group_fill_temporal(
                groups, groupby, aggregates, **fill_temporal
            )

        return self._web_read_group_format(groupby, aggregates, groups)

    def _web_read_group_format(
        self,
        groupby: tuple[str, ...],
        aggregates: tuple[str, ...],
        groups: list[tuple],
    ) -> list[dict]:
        """Format raw value of _read_group for the webclient.
        See formatted_read_group return value."""
        result = [{"__extra_domains": []} for __ in groups]
        if not groups:
            return result
        column_iterator = zip(*groups, strict=True)

        expand_field = self._web_read_group_field_expand(groupby)
        for groupby_spec, values in zip(
            groupby, column_iterator
        ):  # noqa: B905 - intentionally non-strict: column_iterator may yield fewer columns than groupby specs when groups are empty
            # Detect simple scalar fields (selection, char, integer, boolean,
            # float) where the formatter is just identity + equality domain.
            # Inlining avoids closure creation and per-value call overhead.
            field_path = groupby_spec.split(":")[0]
            field_name = field_path.split(".")[0]
            field = self._fields[field_name]
            is_simple = (
                "." not in field_path
                and ":" not in groupby_spec
                and field.type
                not in (
                    "many2one",
                    "many2many",
                    "date",
                    "datetime",
                    "properties",
                )
                and field_name != "id"
            )

            if is_simple:
                for value, dict_group in zip(values, result, strict=True):
                    dict_group[groupby_spec] = value
                    dict_group["__extra_domains"].append([(field_name, "=", value)])
            else:
                formatter = self._web_read_group_groupby_formatter(groupby_spec, values)
                for value, dict_group in zip(values, result, strict=True):
                    dict_group[groupby_spec], additional_domain = formatter(value)
                    dict_group["__extra_domains"].append(additional_domain)

            # Add fold information only if read_group_expand is activated (for kanban/list)
            if expand_field and expand_field.relational:
                model = self.env[expand_field.comodel_name]
                fold_name = model._fold_name
                if fold_name not in model._fields:
                    continue
                for value, dict_group in zip(values, result, strict=True):
                    dict_group["__fold"] = value.sudo()[fold_name]

        # Reconstruct groups domain part
        for dict_group in result:
            dict_group["__extra_domain"] = AND(dict_group.pop("__extra_domains"))

        for aggregate_spec, values in zip(aggregates, column_iterator, strict=True):
            for value, dict_group in zip(values, result, strict=True):
                dict_group[aggregate_spec] = value

        return result

    @api.model
    @api.readonly
    def read_progress_bar(self, domain, group_by, progress_bar):
        """
        Gets the data needed for all the kanban column progressbars.
        These are fetched alongside read_group operation.

        :param domain: the domain used in the kanban view to filter records
        :param group_by: the name of the field used to group records into
            kanban columns
        :param progress_bar: the ``<progressbar/>`` declaration
            attributes (field, colors, sum)
        :return: a dictionnary mapping group_by values to dictionnaries mapping
            progress bar field values to the related number of records
        """

        def adapt(value):
            if isinstance(value, BaseModel):
                return value.id
            return value

        result = defaultdict(lambda: dict.fromkeys(progress_bar["colors"], 0))

        for main_group, field_value, count in self._read_group(
            domain,
            [group_by, progress_bar["field"]],
            ["__count"],
        ):
            if field_value in progress_bar["colors"]:
                group_by_value = str(adapt(main_group))
                result[group_by_value][field_value] += count

        return result
