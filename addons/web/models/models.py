from __future__ import annotations

import base64
import itertools
import json
import typing
from collections import defaultdict
from typing import Any

import babel
import babel.dates
import datetime
import pytz

from odoo import api, models
from odoo.fields import Command, Date, Domain
from odoo.api import NewId
from odoo.models import regex_order, READ_GROUP_DISPLAY_FORMAT, READ_GROUP_NUMBER_GRANULARITY, READ_GROUP_TIME_GRANULARITY, BaseModel
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, date_utils, get_lang, unique, OrderedSet
from odoo.exceptions import AccessError, UserError
from odoo.tools.translate import LazyTranslate

if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from odoo.orm.types import DomainType

_lt = LazyTranslate(__name__)
SEARCH_PANEL_ERROR_MESSAGE = _lt("Too many items to display.")
MAX_NUMBER_OPENED_GROUPS = 10


class lazymapping(defaultdict):
    def __missing__(self, key):
        value = self.default_factory(key)
        self[key] = value
        return value


def AND(domains):
    return list(Domain.AND(domains))


def OR(domains):
    return list(Domain.OR(domains))



class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    @api.readonly
    def web_name_search(self, name, specification, domain=None, operator='ilike', limit=100):
        id_name_pairs = self.name_search(name, domain, operator, limit)
        if len(specification) == 1 and 'display_name' in specification:
            return [{'id': id, 'display_name': name, '__formatted_display_name': self.with_context(formatted_display_name=True).browse(id).display_name} for id, name in id_name_pairs]
        records = self.browse([id for id, _ in id_name_pairs])
        return records.web_read(specification)

    @api.model
    @api.readonly
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        records = self.search_fetch(domain, specification.keys(), offset=offset, limit=limit, order=order)
        values_records = records.web_read(specification)
        return self._format_web_search_read_results(domain, values_records, offset, limit, count_limit)

    def _format_web_search_read_results(self, domain, records, offset=0, limit=None, count_limit=None):
        if not records:
            return {
                'length': 0,
                'records': [],
            }
        current_length = len(records) + offset
        limit_reached = len(records) == limit
        force_search_count = self.env.context.get('force_search_count')
        count_limit_reached = count_limit and count_limit <= current_length
        if limit and ((limit_reached and not count_limit_reached) or force_search_count):
            length = self.search_count(domain, limit=count_limit)
        else:
            length = current_length
        return {
            'length': length,
            'records': records,
        }

    def web_save(self, vals, specification: dict[str, dict], next_id=None) -> list[dict]:
        if self:
            self.write(vals)
        else:
            self = self.create(vals)
        if next_id:
            self = self.browse(next_id)
        return self.with_context(bin_size=True).web_read(specification)

    def web_save_multi(self, vals_list: list[dict], specification: dict[str, dict]) -> list[dict]:
        if len(self) != len(vals_list):
            raise ValueError("Each record must have a corresponding vals entry.")

        for record, val in zip(self, vals_list):
            record.write(val)

        return self.with_context(bin_size=True).web_read(specification)

    @api.readonly
    def web_read(self, specification: dict[str, dict]) -> list[dict]:
        fields_to_read = list(specification) or ['id']

        if fields_to_read == ['id']:
            # if we request to read only the ids, we have them already so we can build the return dictionaries immediately
            # this also avoid a call to read on the co-model that might have different access rules
            values_list = [{'id': id_} for id_ in self._ids]
        else:
            values_list: list[dict] = self.read(fields_to_read, load=None)

        if not values_list:
            return values_list

        def cleanup(vals: dict) -> dict:
            """ Fixup vals['id'] of a new record. """
            if not vals['id']:
                vals['id'] = vals['id'].origin or False
            return vals

        for field_name, field_spec in specification.items():
            field = self._fields.get(field_name)
            if field is None:
                continue

            if field.type == 'many2one':
                if 'fields' not in field_spec:
                    for values in values_list:
                        if isinstance(values[field_name], NewId):
                            values[field_name] = values[field_name].origin
                    continue

                co_records = self[field_name]
                if 'context' in field_spec:
                    co_records = co_records.with_context(**field_spec['context'])

                extra_fields = dict(field_spec['fields'])
                extra_fields.pop('display_name', None)

                many2one_data = {
                    vals['id']: cleanup(vals)
                    for vals in co_records.web_read(extra_fields)
                }

                if 'display_name' in field_spec['fields']:
                    for rec in co_records.sudo():
                        many2one_data[rec.id]['display_name'] = rec.display_name

                for values in values_list:
                    if values[field_name] is False:
                        continue
                    vals = many2one_data[values[field_name]]
                    values[field_name] = vals['id'] and vals

            elif field.type in ('one2many', 'many2many'):
                if not field_spec:
                    continue

                co_records = self[field_name]

                if 'order' in field_spec and field_spec['order']:
                    co_records = co_records.with_context(active_test=False).search(
                        [('id', 'in', co_records.ids)], order=field_spec['order'],
                    ).with_context(co_records.env.context)  # Reapply previous context
                    order_key = {
                        co_record.id: index
                        for index, co_record in enumerate(co_records)
                    }
                    for values in values_list:
                        # filter out inaccessible corecords in case of "cache pollution"
                        values[field_name] = [id_ for id_ in values[field_name] if id_ in order_key]
                        values[field_name] = sorted(values[field_name], key=order_key.__getitem__)

                if 'context' in field_spec:
                    co_records = co_records.with_context(**field_spec['context'])

                if 'fields' in field_spec:
                    if field_spec.get('limit') is not None:
                        limit = field_spec['limit']
                        ids_to_read = OrderedSet(
                            id_
                            for values in values_list
                            for id_ in values[field_name][:limit]
                        )
                        co_records = co_records.browse(ids_to_read)

                    x2many_data = {
                        vals['id']: vals
                        for vals in co_records.web_read(field_spec['fields'])
                    }

                    for values in values_list:
                        values[field_name] = [x2many_data.get(id_) or {'id': id_} for id_ in values[field_name]]

            elif field.type in ('reference', 'many2one_reference'):
                if not field_spec:
                    continue

                values_by_id = {
                    vals['id']: vals
                    for vals in values_list
                }
                for record in self:
                    if not record[field_name]:
                        continue

                    record_values = values_by_id[record.id]

                    if field.type == 'reference':
                        co_record = record[field_name]
                    else:  # field.type == 'many2one_reference'
                        if not record[field.model_field]:
                            record_values[field_name] = False
                            continue
                        co_record = self.env[record[field.model_field]].browse(record[field_name])

                    if 'context' in field_spec:
                        co_record = co_record.with_context(**field_spec['context'])

                    if 'fields' in field_spec:
                        try:
                            reference_read = co_record.web_read(field_spec['fields'])
                        except AccessError:
                            reference_read = [{'id': co_record.id, 'display_name': self.env._("You don't have access to this record")}]
                        if any(fname != 'id' for fname in field_spec['fields']):
                            # we can infer that if we can read fields for the co-record, it exists
                            co_record_exists = bool(reference_read)
                        else:
                            co_record_exists = co_record.exists()
                    else:
                        # If there are no fields to read (field_spec.get('fields') --> None) and we web_read ids, it will
                        # not actually read the records so we do not know if they exist.
                        # This ensures the record actually exists
                        co_record_exists = co_record.exists()

                    if not co_record_exists:
                        record_values[field_name] = False
                        if field.type == 'many2one_reference':
                            record_values[field.model_field] = False
                        continue

                    if 'fields' in field_spec:
                        record_values[field_name] = reference_read[0]
                        if field.type == 'reference':
                            record_values[field_name]['id'] = {
                                'id': co_record.id,
                                'model': co_record._name
                            }

            elif field.type == "properties":
                if not field_spec or 'fields' not in field_spec:
                    continue

                for values in values_list:
                    old_values = values[field_name]
                    next_values = []
                    for property_name, spec in field_spec['fields'].items():
                        property_ = next((p for p in old_values if p.get('name') == property_name), None)
                        if not property_:
                            continue

                        if property_.get('type') == 'many2one' and property_.get('comodel') and property_.get('value'):
                            record = self.env[property_['comodel']].with_context(field_spec.get('context')).browse(property_['value'][0])
                            property_['value'] = record.web_read(spec['fields']) if 'fields' in spec else property_['value']

                        if property_.get('type') == 'many2many' and property_.get('comodel') and property_.get('value'):
                            records = self.env[property_['comodel']].with_context(field_spec.get('context')).browse([r[0] for r in property_['value']])
                            property_['value'] = records.web_read(spec['fields']) if 'fields' in spec else property_['value']

                        next_values.append(property_)

                    values[field_name] = next_values

        return values_list

    def web_resequence(self, specification: dict[str, dict], field_name: str = 'sequence', offset: int = 0) -> list[dict]:
        """ Re-sequences a number of records in the model, by their ids.

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

        for i, record in enumerate(self, start=offset):
            record.write({field_name: i})
        return self.web_read(specification)

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
        unfold_read_default_limit: int | None = 80,  # Limit of record by unfolded group by default
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
        assert isinstance(groupby, (list, tuple)) and groupby

        aggregates = list(aggregates)
        if '__count' not in aggregates:  # Used for computing length of sublevel groups
            aggregates.append('__count')
        domain = Domain(domain).optimize(self)

        # dict to help creating order compatible with _read_group and for search
        dict_order: dict[str, str] = {}  # {fname_and_property: "<direction> <nulls>"}
        for order_part in (order.split(',') if order else ()):
            order_match = regex_order.match(order_part)
            if not order_match:
                raise ValueError(f"Invalid order {order!r} for web_read_group()")
            fname_and_property = order_match['field']
            if order_match['property']:
                fname_and_property = f"{fname_and_property}.{order_match['property']}"
            direction = (order_match['direction'] or 'ASC').upper()
            if order_match['nulls']:
                direction = f"{direction} {order_match['nulls'].upper()}"
            dict_order[fname_and_property] = direction

        # First level of grouping
        first_groupby = [groupby[0]]
        read_group_order = self._get_read_group_order(dict_order, first_groupby, aggregates)
        groups, length = self._formatted_read_group_with_length(
            domain, first_groupby, aggregates, offset=offset, limit=limit, order=read_group_order,
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
                if fname != '__count'
            ]
            for order_str in self._order.split(','):
                fname = order_str.strip().split(" ", 1)[0]
                if fname not in dict_order and fname not in groupby:
                    order_specs.append(order_str)

            order_searches = ', '.join(order_specs)
            recordset_groups = [
                self.search(
                    domain & sub_search['domain'],
                    order=order_searches,
                    limit=sub_search['limit'],
                    offset=sub_search['offset'],
                ) if sub_search['group']['__count'] else self.browse()
                for sub_search in records_opening_info
            ]

            all_records = self.browse().union(*recordset_groups)
            record_mapped = dict(zip(
                all_records._ids,
                all_records.web_read(unfold_read_specification),
                strict=True,
            ))

            for opening, records in zip(records_opening_info, recordset_groups, strict=True):
                opening['group']['__records'] = [record_mapped[record_id] for record_id in records._ids]

        # Read additional info of grouped field record and add it to specific groups
        self._add_groupby_values(groupby_read_specification, groupby, groups)

        return {
            'groups': groups,
            'length': length,
        }

    def _formatted_read_group_with_length(self, domain, groupby, aggregates, offset=0, limit=None, order=None):
        groups = self.formatted_read_group(
            domain, groupby, aggregates, offset=offset, limit=limit, order=order)

        if not groups:
            length = 0
        elif limit and len(groups) == limit:
            length = limit + len(self._read_group(
                domain,
                groupby=groupby,
                offset=limit,
            ))
        else:
            length = len(groups) + offset

        return groups, length

    def _add_groupby_values(self, groupby_read_specification: dict[str, dict] | None, groupby: list[str], current_groups: list):
        if not groupby_read_specification or groupby_read_specification.keys().isdisjoint(groupby):
            return

        for groupby_spec in groupby:
            if groupby_spec in groupby_read_specification:
                relational_field = self._fields[groupby_spec]
                assert relational_field.comodel_name, "We can only read extra info from a relational field"
                group_ids = [
                    id_label[0] for group in current_groups if (id_label := group[groupby_spec])
                ]
                records = self.env[relational_field.comodel_name].browse(group_ids)

                result_read = records.web_read(groupby_read_specification[groupby_spec])
                result_read_map = dict(zip(records._ids, result_read, strict=True))
                for group in current_groups:
                    id_label = group[groupby_spec]
                    group['__values'] = result_read_map[id_label[0]] if id_label else {'id': False}

            current_groups = [
                subgroup
                for group in current_groups
                for subgroup in group.get('__groups', {}).get('groups', ())
            ]

    def _get_read_group_order(self, dict_order: dict[str, str], groupby: list[str], aggregates: Sequence[str]) -> str:
        if not dict_order:
            return ", ".join(groupby)

        groupby = list(groupby)
        order_spec = []
        for fname, direction in dict_order.items():
            if fname == '__count':
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
        max_number_opened_group = self.env.context.get('max_number_opened_groups') or MAX_NUMBER_OPENED_GROUPS

        parent_opening_info_dict = {
            info_opening['value']: info_opening
            for info_opening in parent_opening_info or ()
        }
        groupby_spec = groupby[0]
        field = self._fields[groupby_spec.split(':')[0].split('.')[0]]
        nb_opened_group = 0

        last_level = len(groupby) == 1
        if not last_level:
            read_group_order = self._get_read_group_order(dict_order, [groupby[1]], aggregates)

        for group in groups:
            # Remove __fold information, no need for the webclient,
            # the groups is unfold if __groups/__records exists
            fold_info = '__fold' in group
            fold = group.pop('__fold', False)

            groupby_value = group[groupby_spec]
            # For relational/date/datetime field
            raw_groupby_value = groupby_value[0] if isinstance(groupby_value, tuple) else groupby_value

            limit = unfold_read_default_limit
            offset = 0
            progressbar_domain = subgroup_opening_info = None
            if opening_info and raw_groupby_value in parent_opening_info_dict:
                group_info = parent_opening_info_dict[raw_groupby_value]
                if group_info['folded']:
                    continue
                limit = group_info['limit']
                offset = group_info['offset']
                progressbar_domain = group_info.get('progressbar_domain')
                subgroup_opening_info = group_info.get('groups')

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
                records_domain = parent_group_domain & Domain(group['__extra_domain'])

                # when we click on a part of the progress bar, we force a domain
                # for a specific open column/group, we want to keep this for the next reload
                if progressbar_domain:
                    records_domain &= Domain(progressbar_domain)

                # TODO also for groups ?
                # Simulate the same behavior than in relational_model.js
                # If the offset is bigger than the number of record (a record has been deleted)
                # reset the offset to 0 and add the information to the group to update the webclient too
                if offset and offset >= group['__count']:
                    group['__offset'] = offset = 0

                records_opening_info.append({
                    'domain': records_domain,
                    'limit': limit,
                    'offset': offset,
                    'group': group,
                })

            else:  # Open subgroups

                subgroup_domain = parent_group_domain
                if group['__extra_domain']:
                    subgroup_domain &= Domain(group['__extra_domain'])
                # That's not optimal but hard to batch because of limit/offset.
                # Moreover it isn't critical since it is when user opens group manually, then
                # the number of it should be small.
                subgroups, length = self._formatted_read_group_with_length(
                    domain=(subgroup_domain & domain),
                    groupby=[groupby[1]], aggregates=aggregates,
                    offset=offset, limit=limit, order=read_group_order)

                group['__groups'] = {
                    'groups': subgroups,
                    'length': length,
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
        aggregates = tuple(agg.replace(':recordset', ':array_agg') for agg in aggregates)

        if not order:
            order = ', '.join(unique(spec for groupby in grouping_sets for spec in groupby))

        groups_list = self._read_grouping_sets(
            domain, grouping_sets, aggregates, order=order,
        )

        for groups_index, groupby in enumerate(grouping_sets):
            if self._web_read_group_field_expand(groupby):
                groups_list[groups_index] = self._web_read_group_expand(domain, groups_list[groups_index], groupby[0], aggregates, order)

        for groups_index, groupby in enumerate(grouping_sets):
            fill_temporal = self.env.context.get('fill_temporal')
            if groupby and (fill_temporal or isinstance(fill_temporal, dict)):
                if not isinstance(fill_temporal, dict):
                    fill_temporal = {}
                # This assumes that existing data is sorted by field 'groupby_name'
                groups_list[groups_index] = self._web_read_group_fill_temporal(groups_list[groups_index], groupby, aggregates, **fill_temporal)

        return [
            self._web_read_group_format(groupby, aggregates, groups)
            for groupby, groups in zip(grouping_sets, groups_list)
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
        aggregates = tuple(agg.replace(':recordset', ':array_agg') for agg in aggregates)

        if not order:
            order = ', '.join(groupby)

        groups = self._read_group(
            domain, groupby, aggregates,
            having=having, offset=offset, limit=limit, order=order,
        )

        # Note: group_expand is only done if the limit isn't reached and when the offset == 0
        # to avoid inconsistency in the web client pager. Anyway, in practice, this feature should
        # be used only when there are few groups (or without limit for the kanban view).
        if (
            not offset and (not limit or len(groups) < limit)
            and self._web_read_group_field_expand(groupby)
        ):
            # It doesn't respect the order with aggregates inside
            expand_groups = self._web_read_group_expand(domain, groups, groupby[0], aggregates, order)
            if not limit or len(expand_groups) < limit:
                # Ditch the result of expand_groups because the limit is reached and to avoid
                # returning inconsistent result inside length of web_read_group
                groups = expand_groups

        fill_temporal = self.env.context.get('fill_temporal')
        if groupby and (fill_temporal or isinstance(fill_temporal, dict)):
            if limit or offset:
                raise ValueError('You cannot used fill_temporal with a limit or an offset')
            if not isinstance(fill_temporal, dict):
                fill_temporal = {}
            # This assumes that existing data is sorted by field 'groupby_name'
            groups = self._web_read_group_fill_temporal(groups, groupby, aggregates, **fill_temporal)

        return self._web_read_group_format(groupby, aggregates, groups)

    def _web_read_group_field_expand(self, groupby):
        """ Return the field that should be expand """
        if (
            len(groupby) == 1
            and self.env.context.get('read_group_expand')
            and '.' not in groupby[0]
            and (field := self._fields[groupby[0].split(':')[0]])
            and field.group_expand
        ):
            return field
        return None

    def _web_read_group_expand(self, domain, groups, groupby_spec, aggregates, order):
        """ Expand the result of _read_group for the webclient to show empty groups
        for some view types (e.g. empty column for kanban view). See `Field.group_expand` attribute.
        """
        field_name = groupby_spec.split('.')[0].split(':')[0]
        field = self._fields[field_name]

        # determine all groups that should be returned
        values = [group_value for group_value, *__ in groups if group_value]

        # field.group_expand is a callable or the name of a method, that returns
        # the groups that we want to display for this field, in the form of a
        # recordset or a list of values (depending on the type of the field).
        # This is useful to implement kanban views for instance, where some
        # columns should be displayed even if they don't contain any record.
        if field.relational:
            # groups is a recordset; determine order on groups's model
            values = self.env[field.comodel_name].browse(value.id for value in values)
            expand_values = field.determine_group_expand(self, values, domain)
            all_record_ids = tuple(unique(expand_values._ids + values._ids))
        else:
            # groups is a list of values
            expand_values = field.determine_group_expand(self, values, domain)

        if (groupby_spec + ' desc') in order.lower():
            expand_values = reversed(expand_values)

        empty_aggregates = tuple(self._read_group_empty_value(spec) for spec in aggregates)
        result = dict.fromkeys(expand_values, empty_aggregates)
        result.update({
            group_value: aggregate_values
            for group_value, *aggregate_values in groups
        })

        if field.relational:
            return [
                (value.with_prefetch(all_record_ids), *aggregate_values)
                for value, aggregate_values in result.items()
            ]
        return [(value, *aggregate_values) for value, aggregate_values in result.items()]

    @api.model
    def _web_read_group_fill_temporal(self, groups, groupby, aggregates, fill_from=False, fill_to=False, min_groups=False):
        """Helper method for filling date/datetime 'holes' in a result for the first groupby.

        We are in a use case where data are grouped by a date field (typically
        months but it could be any other interval) and displayed in a chart.

        Assume we group records by month, and we only have data for June,
        September and December. By default, plotting the result gives something
        like::

                                                ___
                                      ___      |   |
                                     |   | ___ |   |
                                     |___||___||___|
                                      Jun  Sep  Dec

        The problem is that December data immediately follow September data,
        which is misleading for the user. Adding explicit zeroes for missing
        data gives something like::

                                                           ___
                             ___                          |   |
                            |   |           ___           |   |
                            |___| ___  ___ |___| ___  ___ |___|
                             Jun  Jul  Aug  Sep  Oct  Nov  Dec

        To customize this output, the context key "fill_temporal" can be used
        under its dictionary format, which has 3 attributes : fill_from,
        fill_to, min_groups (see params of this function)

        Fill between bounds:
        Using either `fill_from` and/or `fill_to` attributes, we can further
        specify that at least a certain date range should be returned as
        contiguous groups. Any group outside those bounds will not be removed,
        but the filling will only occur between the specified bounds. When not
        specified, existing groups will be used as bounds, if applicable.
        By specifying such bounds, we can get empty groups before/after any
        group with data.

        If we want to fill groups only between August (fill_from)
        and October (fill_to)::

                                                     ___
                                 ___                |   |
                                |   |      ___      |   |
                                |___| ___ |___| ___ |___|
                                 Jun  Aug  Sep  Oct  Dec

        We still get June and December. To filter them out, we should match
        `fill_from` and `fill_to` with the domain e.g. ``['&',
        ('date_field', '>=', 'YYYY-08-01'), ('date_field', '<', 'YYYY-11-01')]``::

                                         ___
                                    ___ |___| ___
                                    Aug  Sep  Oct

        Minimal filling amount:
        Using `min_groups`, we can specify that we want at least that amount of
        contiguous groups. This amount is guaranteed to be provided from
        `fill_from` if specified, or from the lowest existing group otherwise.
        This amount is not restricted by `fill_to`. If there is an existing
        group before `fill_from`, `fill_from` is still used as the starting
        group for min_groups, because the filling does not apply on that
        existing group. If neither `fill_from` nor `fill_to` is specified, and
        there is no existing group, no group will be returned.

        If we set min_groups = 4::

                                         ___
                                    ___ |___| ___ ___
                                    Aug  Sep  Oct Nov

        :param list groups: groups returned by _read_group
        :param list groupby: list of fields being grouped on
        :param list aggregates: list of "<key_name>:<aggregate specification>"
        :param str fill_from: (inclusive) string representation of a
            date/datetime, start bound of the fill_temporal range
            formats: date -> %Y-%m-%d, datetime -> %Y-%m-%d %H:%M:%S
        :param str fill_to: (inclusive) string representation of a
            date/datetime, end bound of the fill_temporal range
            formats: date -> %Y-%m-%d, datetime -> %Y-%m-%d %H:%M:%S
        :param int min_groups: minimal amount of required groups for the
            fill_temporal range (should be >= 1)
        :rtype: list
        :return: list
        """
        groupby_name = groupby[0]
        field_name = groupby_name.split(':')[0].split(".")[0]
        field = self._fields[field_name]
        if field.type not in ('date', 'datetime') and not (field.type == 'properties' and ':' in groupby_name):
            return groups

        granularity = groupby_name.split(':')[1]
        days_offset = 0
        if granularity == 'week':
            # _read_group week groups are dependent on the
            # locale, so filled groups should be too to avoid overlaps.
            first_week_day = int(get_lang(self.env).week_start) - 1
            days_offset = first_week_day and 7 - first_week_day
        tz = False
        if field.type == 'datetime' and self.env.context.get('tz') in pytz.all_timezones_set:
            tz = pytz.timezone(self.env.context['tz'])

        # existing non null date(time)
        existing = sorted(group_value for group in groups if (group_value := group[0])) or [None]
        # assumption: existing data is sorted by field 'groupby_name'
        existing_from, existing_to = existing[0], existing[-1]
        if fill_from:
            fill_from = Date.to_date(fill_from)
            fill_from = date_utils.start_of(fill_from, granularity) - datetime.timedelta(days=days_offset)
            if tz:
                fill_from = tz.localize(fill_from)
        elif existing_from:
            fill_from = existing_from
        if fill_to:
            fill_to = Date.to_date(fill_to)
            fill_to = date_utils.start_of(fill_to, granularity) - datetime.timedelta(days=days_offset)
            if tz:
                fill_to = tz.localize(fill_to)
        elif existing_to:
            fill_to = existing_to

        if not fill_to and fill_from:
            fill_to = fill_from
        elif not fill_from and fill_to:
            fill_from = fill_to
        if not fill_from and not fill_to:
            return groups

        interval = READ_GROUP_TIME_GRANULARITY[granularity]
        if min_groups > 0:
            fill_to = max(fill_to, fill_from + (min_groups - 1) * interval)

        if fill_from > fill_to:
            return groups

        empty_item = tuple(self._read_group_empty_value(spec) for spec in groupby[1:] + aggregates)
        required_dates = list(date_utils.date_range(fill_from, fill_to, interval))

        if existing[0] is None:
            existing = list(required_dates)
        else:
            existing = sorted(set().union(existing, required_dates))

        groups_mapped = defaultdict(list)
        for group in groups:
            groups_mapped[group[0]].append(group)

        result = []
        for dt in existing:
            if dt in groups_mapped:
                result.extend(groups_mapped[dt])
            else:
                result.append((dt, *empty_item))

        if False in groups_mapped:
            result.extend(groups_mapped[False])

        return result

    def _web_read_group_format(
        self,
        groupby: tuple[str, ...],
        aggregates: tuple[str, ...],
        groups: list[tuple],
    ) -> list[dict]:
        """ Format raw value of _read_group for the webclient.
        See formatted_read_group return value. """
        result = [{'__extra_domains': []} for __ in groups]
        if not groups:
            return result
        column_iterator = zip(*groups)

        for groupby_spec, values in zip(groupby, column_iterator):
            formatter = self._web_read_group_groupby_formatter(groupby_spec, values)
            for value, dict_group in zip(values, result, strict=True):
                dict_group[groupby_spec], additional_domain = formatter(value)
                dict_group['__extra_domains'].append(additional_domain)

            # Add fold information only if read_group_expand is activated (for kanban/list)
            if ((field := self._web_read_group_field_expand(groupby)) and field.relational):
                model = self.env[field.comodel_name]
                fold_name = model._fold_name
                if fold_name not in model._fields:
                    continue
                for value, dict_group in zip(values, result):
                    dict_group['__fold'] = value.sudo()[fold_name]

        # Reconstruct groups domain part
        for dict_group in result:
            dict_group['__extra_domain'] = AND(dict_group.pop('__extra_domains'))

        for aggregate_spec, values in zip(aggregates, column_iterator, strict=True):
            for value, dict_group in zip(values, result, strict=True):
                dict_group[aggregate_spec] = value

        return result

    def _web_read_group_groupby_formatter(self, groupby_spec, values):
        """ Return a formatter method that returns value/label and the domain that the group
        value represent """
        field_path = groupby_spec.split(':')[0]
        field_name, _dot, remaining_path = field_path.partition('.')
        field = self._fields[field_name]

        if remaining_path and field.type == 'many2one':
            model = self.env[field.comodel_name]
            sub_formatter = model._web_read_group_groupby_formatter(groupby_spec.split('.', 1)[1], values)

            def formatter_follow_many2one(value):
                value, domain = sub_formatter(value)
                if not value:
                    return value, ['|', (field_name, 'not any', []), (field_name, 'any', domain)]
                return value, [(field_name, 'any', domain)]

            return formatter_follow_many2one

        if field.type == 'many2many':

            # Special case for many2many because (<many2many>, '=', False) domain bypass ir.rule.
            def formatter_many2many(value):
                if not value:
                    return False, [(field_name, 'not any', [])]
                id_ = value.id
                return (id_, value.sudo().display_name), [(field_name, '=', id_)]

            return formatter_many2many

        if field.type == 'many2one' or field_name == 'id':

            def formatter_many2one(value):
                if not value:
                    return False, [(field_name, '=', False)]
                id_ = value.id
                return (id_, value.sudo().display_name), [(field_name, '=', id_)]

            return formatter_many2one

        if field.type in ('date', 'datetime'):
            assert ':' in groupby_spec, "Granularity is missing"
            granularity = groupby_spec.split(':')[1]
            if granularity in READ_GROUP_TIME_GRANULARITY:
                locale = get_lang(self.env).code
                fmt = DEFAULT_SERVER_DATETIME_FORMAT if field.type == 'datetime' else DEFAULT_SERVER_DATE_FORMAT
                interval = READ_GROUP_TIME_GRANULARITY[granularity]

                def formatter_time_granularity(value):
                    if not value:
                        return value, [(field_name, '=', value)]
                    range_start = value
                    range_end = value + interval
                    if field.type == 'datetime':
                        tzinfo = None
                        if self.env.context.get('tz') in pytz.all_timezones_set:
                            tzinfo = pytz.timezone(self.env.context['tz'])
                            range_start = tzinfo.localize(range_start).astimezone(pytz.utc)
                            # take into account possible hour change between start and end
                            range_end = tzinfo.localize(range_end).astimezone(pytz.utc)

                        label = babel.dates.format_datetime(
                            range_start, format=READ_GROUP_DISPLAY_FORMAT[granularity],
                            tzinfo=tzinfo, locale=locale,
                        )
                    else:
                        label = babel.dates.format_date(
                            value, format=READ_GROUP_DISPLAY_FORMAT[granularity],
                            locale=locale,
                        )

                    # special case weeks because babel is broken *and*
                    # ubuntu reverted a change so it's also inconsistent
                    if granularity == 'week':
                        year, week = date_utils.weeknumber(
                            babel.Locale.parse(locale),
                            value,  # provide date or datetime without UTC conversion
                        )
                        label = f"W{week} {year:04}"

                    additional_domain = ['&',
                        (field_name, '>=', range_start.strftime(fmt)),
                        (field_name, '<', range_end.strftime(fmt)),
                    ]
                    # TODO: date label should be created by the webclient.
                    return (range_start.strftime(fmt), label), additional_domain

                return formatter_time_granularity

            if granularity in READ_GROUP_NUMBER_GRANULARITY:

                def formatter_date_number_granularity(value):
                    if value is None:
                        return [(field_name, '=', value)]
                    return value, [(f"{field_name}.{granularity}", '=', value)]

                return formatter_date_number_granularity

            raise ValueError(f"{granularity!r} isn't a valid granularity")

        if field.type == "properties":
            return self._web_read_group_groupby_properties_formatter(groupby_spec, values)

        return lambda value: (value, [(field_name, '=', value)])

    def _web_read_group_groupby_properties_formatter(self, groupby_spec, values):
        if '.' not in groupby_spec:
            raise ValueError('You must choose the property you want to group by.')

        fullname, __, func = groupby_spec.partition(':')
        definition = self.get_property_definition(fullname)
        property_type = definition.get('type')
        if property_type == 'selection':
            options = definition.get('selection') or []
            options = tuple(option[0] for option in options)

            def formatter_property_selection(value):
                if not value:
                    # can not do ('selection', '=', False) because we might have
                    # option in database that does not exist anymore
                    return value, ['|', (fullname, '=', False), (fullname, 'not in', options)]
                return value, [(fullname, '=', value)]

            return formatter_property_selection

        if property_type == 'many2one':
            comodel = definition['comodel']
            all_groups = tuple(value for value in values if value)

            def formatter_property_many2one(value):
                if not value:
                    # can not only do ('many2one', '=', False) because we might have
                    # record in database that does not exist anymore
                    return value, ['|', (fullname, '=', False), (fullname, 'not in', all_groups)]
                record = self.env[comodel].browse(value).with_prefetch(all_groups)
                return (value, record.display_name), [(fullname, '=', value)]

            return formatter_property_many2one

        if property_type == 'many2many':
            comodel = definition['comodel']
            all_groups = tuple(value for value in values if value)

            def formatter_property_many2many(value):
                if not value:
                    return value, OR([
                        [(fullname, '=', False)],
                        AND([[(fullname, 'not in', group)] for group in all_groups]),
                    ]) if all_groups else []
                record = self.env[comodel].browse(value).with_prefetch(all_groups)
                return (value, record.display_name), [(fullname, 'in', value)]

            return formatter_property_many2many

        if property_type == 'tags':
            tags = definition.get('tags') or []
            tags = {tag[0]: tag for tag in tags}

            def formatter_property_tags(value):
                if not value:
                    return value, OR([
                        [(fullname, '=', False)],
                        AND([[(fullname, 'not in', tag)] for tag in tags]),
                    ]) if tags else []

                # replace tag raw value with list of raw value, label and color
                return tags.get(value), [(fullname, 'in', value)]

            return formatter_property_tags

        if property_type in ('date', 'datetime'):

            def formatter_property_datetime(value):
                if not value:
                    return False, [(fullname, '=', False)]

                # Date / Datetime are not JSONifiable, so they are stored as raw text
                db_format = '%Y-%m-%d' if property_type == 'date' else '%Y-%m-%d %H:%M:%S'
                fmt = DEFAULT_SERVER_DATE_FORMAT if property_type == 'date' else DEFAULT_SERVER_DATETIME_FORMAT

                if func == 'week':
                    # the value is the first day of the week (based on local)
                    start = value.strftime(db_format)
                    end = (value + datetime.timedelta(days=7)).strftime(db_format)
                else:
                    start = (date_utils.start_of(value, func)).strftime(db_format)
                    end = (date_utils.end_of(value, func) + datetime.timedelta(minutes=1)).strftime(db_format)

                label = babel.dates.format_date(
                    value,
                    format=READ_GROUP_DISPLAY_FORMAT[func],
                    locale=get_lang(self.env).code,
                )
                return (value.strftime(fmt), label), [(fullname, '>=', start), (fullname, '<', end)]

            return formatter_property_datetime

        return lambda value: (value, [(fullname, '=', value)])


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

        result = defaultdict(lambda: dict.fromkeys(progress_bar['colors'], 0))

        for main_group, field_value, count in self._read_group(
            domain, [group_by, progress_bar['field']], ['__count'],
        ):
            if field_value in progress_bar['colors']:
                group_by_value = str(adapt(main_group))
                result[group_by_value][field_value] += count

        return result

    @api.model
    def _search_panel_field_image(self, field_name, **kwargs):
        """
        Return the values in the image of the provided domain by field_name.

        :param model_domain: domain whose image is returned
        :param extra_domain: extra domain to use when counting records
            associated with field values
        :param field_name: the name of a field (type ``many2one`` or
            ``selection``)
        :param enable_counters: whether to set the key ``'__count'`` in
            image values
        :param only_counters: whether to retrieve information on the
            ``model_domain`` image or only counts based on
            ``model_domain`` and ``extra_domain``. In the later case,
            the counts are set whatever is enable_counters.
        :param limit: maximal number of values to fetch
        :param bool set_limit: whether to use the provided limit (if any)
        :return: a dict of the form:
            ::

                {
                    id: { 'id': id, 'display_name': display_name, ('__count': c,) },
                    ...
                }
        """

        enable_counters = kwargs.get('enable_counters')
        only_counters = kwargs.get('only_counters')
        extra_domain = Domain(kwargs.get('extra_domain', []))
        no_extra = extra_domain.is_true()
        model_domain = Domain(kwargs.get('model_domain', []))
        count_domain = model_domain & extra_domain

        limit = kwargs.get('limit')
        set_limit = kwargs.get('set_limit')

        if only_counters:
            return self._search_panel_domain_image(field_name, count_domain, True)

        model_domain_image = self._search_panel_domain_image(field_name, model_domain,
                            enable_counters and no_extra,
                            set_limit and limit,
                        )
        if enable_counters and not no_extra:
            count_domain_image = self._search_panel_domain_image(field_name, count_domain, True)
            for id, values in model_domain_image.items():
                element = count_domain_image.get(id)
                values['__count'] = element['__count'] if element else 0

        return model_domain_image

    @api.model
    def _search_panel_domain_image(self, field_name, domain, set_count=False, limit=False):
        """
        Return the values in the image of the provided domain by field_name.

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
        if field.type in ('many2one', 'many2many'):
            def group_id_name(value):
                return value

        else:
            # field type is selection: see doc above
            desc = self.fields_get([field_name], ['selection'])[field_name]
            field_name_selection = dict(desc['selection'])

            def group_id_name(value):
                return value, field_name_selection[value]

        domain = AND([
            domain,
            [(field_name, '!=', False)],
        ])
        groups = self.with_context(read_group_expand=True).formatted_read_group(
            domain, [field_name], ['__count'], limit=limit)

        domain_image = {}
        for group in groups:
            id_, display_name = group_id_name(group[field_name])
            values = {
                'id': id_,
                'display_name': display_name,
            }
            if set_count:
                values['__count'] = group['__count']
            domain_image[id_] = values

        return domain_image


    @api.model
    def _search_panel_global_counters(self, values_range, parent_name):
        """
        Modify in place values_range to transform the (local) counts
        into global counts (local count + children local counts)
        in case a parent field parent_name has been set on the range values.
        Note that we save the initial (local) counts into an auxiliary dict
        before they could be changed in the for loop below.

        :param values_range: dict of the form:
            ::

                {
                    id: { 'id': id, '__count': c, parent_name: parent_id, ... }
                    ...
                }
        :param parent_name: string, indicates which key determines the parent
        """
        local_counters = lazymapping(lambda id: values_range[id]['__count'])

        for id in values_range:
            values = values_range[id]
            # here count is the initial value = local count set on values
            count = local_counters[id]
            if count:
                parent_id = values[parent_name]
                while parent_id:
                    values = values_range[parent_id]
                    local_counters[parent_id]
                    values['__count'] += count
                    parent_id = values[parent_name]

    @api.model
    def _search_panel_sanitized_parent_hierarchy(self, records, parent_name, ids):
        """
        Filter the provided list of records to ensure the following properties of
        the resulting sublist:

        1) it is closed for the parent relation
        2) every record in it is an ancestor of a record with id in ids
           (if ``ids = records.ids``, that condition is automatically
           satisfied)
        3) it is maximal among other sublists with properties 1 and 2.

        :param list[dict] records: the list of records to filter, the
            records must have the form::

                { 'id': id, parent_name: False or (id, display_name),... }

        :param str parent_name: indicates which key determines the parent
        :param list[int] ids: list of record ids
        :return: the sublist of records with the above properties
        """
        def get_parent_id(record):
            value = record[parent_name]
            return value and value[0]

        allowed_records = { record['id']: record for record in records }
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
        return [rec for rec in records if records_to_keep.get(rec['id'])]


    @api.model
    def _search_panel_selection_range(self, field_name, **kwargs):
        """
        Return the values of a field of type selection possibly enriched
        with counts of associated records in domain.

        :param enable_counters: whether to set the key ``'__count'`` on
            values returned. Default is ``False``.
        :param expand: whether to return the full range of values for
            the selection field or only the field image values. Default
            is ``False``.
        :param field_name: the name of a field of type selection
        :param model_domain: domain used to determine the field image
            values and counts. Default is an empty list.
        :return: a list of dicts of the form
            ::

                { 'id': id, 'display_name': display_name, ('__count': c,) }

            with key ``'__count'`` set if ``enable_counters`` is
            ``True``.
        """


        enable_counters = kwargs.get('enable_counters')
        expand = kwargs.get('expand')

        if enable_counters or not expand:
            domain_image = self._search_panel_field_image(field_name, only_counters=expand, **kwargs)

        if not expand:
            return list(domain_image.values())

        selection = self.fields_get([field_name])[field_name]['selection']

        selection_range = []
        for value, label in selection:
            values = {
                'id': value,
                'display_name': label,
            }
            if enable_counters:
                image_element = domain_image.get(value)
                values['__count'] = image_element['__count'] if image_element else 0
            selection_range.append(values)

        return selection_range


    @api.model
    def search_panel_select_range(self, field_name, **kwargs):
        """
        Return possible values of the field field_name (case select="one"),
        possibly with counters, and the parent field (if any and required)
        used to hierarchize them.

        :param field_name: the name of a field; of type many2one or selection.
        :param kwargs: additional features

            :param category_domain: domain generated by categories.
                Default is ``[]``.
            :param comodel_domain: domain of field values (if relational).
                Default is ``[]``.
            :param enable_counters: whether to count records by value.
                Default is ``False``.
            :param expand: whether to return the full range of field values in
                comodel_domain or only the field image values (possibly
                filtered and/or completed with parents if hierarchize is set).
                Default is ``False``.
            :param filter_domain: domain generated by filters.
                Default is ``[]``.
            :param hierarchize: determines if the categories must be displayed
                hierarchically (if possible). If set to true and
                ``_parent_name`` is set on the comodel field, the information
                necessary for the hierarchization will be returned.
                Default is ``True``.
            :param limit: integer, maximal number of values to fetch.
                Default is ``None`` (no limit).
            :param search_domain: base domain of search. Default is ``[]``.

        :return: ::

                {
                    'parent_field': parent field on the comodel of field, or False
                    'values': array of dictionaries containing some info on the records
                              available on the comodel of the field 'field_name'.
                              The display name, the __count (how many records with that value)
                              and possibly parent_field are fetched.
                }

            or an object with an error message when limit is defined and is reached.
        """
        field = self._fields[field_name]
        supported_types = ['many2one', 'selection']
        if field.type not in supported_types:
            types = dict(self.env["ir.model.fields"]._fields["ttype"]._description_selection(self.env))
            raise UserError(self.env._(
                'Only types %(supported_types)s are supported for category (found type %(field_type)s)',
                supported_types=", ".join(types[t] for t in supported_types),
                field_type=types[field.type],
            ))

        model_domain = kwargs.get('search_domain', [])
        extra_domain = AND([
            kwargs.get('category_domain', []),
            kwargs.get('filter_domain', []),
        ])

        if field.type == 'selection':
            return {
                'parent_field': False,
                'values': self._search_panel_selection_range(field_name, model_domain=model_domain,
                                extra_domain=extra_domain, **kwargs
                            ),
            }

        Comodel = self.env[field.comodel_name].with_context(hierarchical_naming=False)
        field_names = ['display_name']
        hierarchize = kwargs.get('hierarchize', True)
        parent_name = False
        if hierarchize and Comodel._parent_name in Comodel._fields:
            parent_name = Comodel._parent_name
            field_names.append(parent_name)

            def get_parent_id(record):
                value = record[parent_name]
                return value and value[0]
        else:
            hierarchize = False

        comodel_domain = kwargs.get('comodel_domain', [])
        enable_counters = kwargs.get('enable_counters')
        expand = kwargs.get('expand')
        limit = kwargs.get('limit')

        if enable_counters or not expand:
            domain_image = self._search_panel_field_image(field_name,
                model_domain=model_domain, extra_domain=extra_domain,
                only_counters=expand,
                set_limit= limit and not (expand or hierarchize or comodel_domain), **kwargs
            )

        if not (expand or hierarchize or comodel_domain):
            values = list(domain_image.values())
            if limit and len(values) == limit:
                return {'error_msg': str(SEARCH_PANEL_ERROR_MESSAGE)}
            return {
                'parent_field': parent_name,
                'values': values,
            }

        if not expand:
            image_element_ids = list(domain_image.keys())
            if hierarchize:
                condition = [('id', 'parent_of', image_element_ids)]
            else:
                condition = [('id', 'in', image_element_ids)]
            comodel_domain = AND([comodel_domain, condition])
        comodel_records = Comodel.search_read(comodel_domain, field_names, limit=limit)

        if hierarchize:
            ids = [rec['id'] for rec in comodel_records] if expand else image_element_ids
            comodel_records = self._search_panel_sanitized_parent_hierarchy(comodel_records, parent_name, ids)

        if limit and len(comodel_records) == limit:
            return {'error_msg': str(SEARCH_PANEL_ERROR_MESSAGE)}

        field_range = {}
        for record in comodel_records:
            record_id = record['id']
            values = {
                'id': record_id,
                'display_name': record['display_name'],
            }
            if hierarchize:
                values[parent_name] = get_parent_id(record)
            if enable_counters:
                image_element = domain_image.get(record_id)
                values['__count'] = image_element['__count'] if image_element else 0
            field_range[record_id] = values

        if hierarchize and enable_counters:
            self._search_panel_global_counters(field_range, parent_name)

        return {
            'parent_field': parent_name,
            'values': list(field_range.values()),
        }


    @api.model
    def search_panel_select_multi_range(self, field_name, **kwargs):
        """
        Return possible values of the field field_name (case select="multi"),
        possibly with counters and groups.

        :param field_name: the name of a filter field;
            possible types are many2one, many2many, selection.

        :param kwargs: additional features

            :param category_domain: domain generated by categories.
                Default is ``[]``.
            :param comodel_domain: domain of field values (if relational)
                    (this parameter is used in :meth:`_search_panel_range`).
                    Default is ``[]``.
            :param enable_counters: whether to count records by value.
                Default is ``False``.
            :param expand: whether to return the full range of field values in
                ``comodel_domain`` or only the field image values.
                Default is ``False``.
            :param filter_domain: domain generated by filters.
                Default is ``[]``.
            :param group_by: extra field to read on comodel, to group comodel
                records.
            :param group_domain: dict, one domain for each activated group for
                the group_by (if any). Those domains are used to fech accurate
                counters for values in each group.
                Default is ``[]`` (many2one case) or ``None``.
            :param limit: integer, maximal number of values to fetch.
                Default is ``None`` (no limit).
            :param search_domain: base domain of search. Default is ``[]``.

        :return: ::

                {
                    'values': a list of possible values, each being a dict with keys
                        'id' (value),
                        'name' (value label),
                        '__count' (how many records with that value),
                        'group_id' (value of group), set if a group_by has been provided,
                        'group_name' (label of group), set if a group_by has been provided
                }

            or an object with an error message when limit is defined and reached.
        """
        field = self._fields[field_name]
        supported_types = ['many2one', 'many2many', 'selection']
        if field.type not in supported_types:
            raise UserError(self.env._(
                'Only types %(supported_types)s are supported for filter (found type %(field_type)s)',
                supported_types=supported_types, field_type=field.type))

        model_domain = kwargs.get('search_domain', [])
        extra_domain = AND([
            kwargs.get('category_domain', []),
            kwargs.get('filter_domain', []),
        ])

        if field.type == 'selection':
            return {
                'values': self._search_panel_selection_range(field_name, model_domain=model_domain,
                                extra_domain=extra_domain, **kwargs
                            )
            }

        Comodel = self.env.get(field.comodel_name).with_context(hierarchical_naming=False)
        field_names = ['display_name']
        group_by = kwargs.get('group_by')
        limit = kwargs.get('limit')
        if group_by:
            group_by_field = Comodel._fields[group_by]

            field_names.append(group_by)

            if group_by_field.type == 'many2one':
                def group_id_name(value):
                    return value or (False, self.env._("Not Set"))

            elif group_by_field.type == 'selection':
                desc = Comodel.fields_get([group_by])[group_by]
                group_by_selection = dict(desc['selection'])
                group_by_selection[False] = self.env._("Not Set")

                def group_id_name(value):
                    return value, group_by_selection[value]

            else:
                def group_id_name(value):
                    return (value, value) if value else (False, self.env._("Not Set"))

        comodel_domain = kwargs.get('comodel_domain', [])
        enable_counters = kwargs.get('enable_counters')
        expand = kwargs.get('expand')

        if field.type == 'many2many':
            if not expand:
                domain_image = self._search_panel_domain_image(field_name, model_domain, limit=limit)
                image_element_ids = list(domain_image.keys())
                comodel_domain = AND([
                    comodel_domain,
                    [('id', 'in', image_element_ids)],
                ])

            comodel_records = Comodel.search_read(comodel_domain, field_names, limit=limit)
            if limit and len(comodel_records) == limit:
                return {'error_msg': str(SEARCH_PANEL_ERROR_MESSAGE)}

            group_domain = kwargs.get('group_domain')
            field_range = []
            for record in comodel_records:
                record_id = record['id']
                values= {
                    'id': record_id,
                    'display_name': record['display_name'],
                }
                if group_by:
                    group_id, group_name = group_id_name(record[group_by])
                    values['group_id'] = group_id
                    values['group_name'] = group_name

                if enable_counters:
                    search_domain = AND([
                            model_domain,
                            [(field_name, 'in', record_id)],
                        ])
                    local_extra_domain = extra_domain
                    if group_by and group_domain:
                        local_extra_domain = AND([
                            local_extra_domain,
                            group_domain.get(json.dumps(group_id), []),
                        ])
                    search_count_domain = AND([
                        search_domain,
                        local_extra_domain
                    ])
                    values['__count'] = self.search_count(search_count_domain)
                field_range.append(values)

            return { 'values': field_range, }

        if field.type == 'many2one':
            if enable_counters or not expand:
                extra_domain = AND([
                    extra_domain,
                    kwargs.get('group_domain', []),
                ])
                domain_image = self._search_panel_field_image(field_name,
                                    model_domain=model_domain, extra_domain=extra_domain,
                                    only_counters=expand,
                                    set_limit=limit and not (expand or group_by or comodel_domain), **kwargs
                                )

            if not (expand or group_by or comodel_domain):
                values = list(domain_image.values())
                if limit and len(values) == limit:
                    return {'error_msg': str(SEARCH_PANEL_ERROR_MESSAGE)}
                return {'values': values, }

            if not expand:
                image_element_ids = list(domain_image.keys())
                comodel_domain = AND([
                    comodel_domain,
                    [('id', 'in', image_element_ids)],
                ])
            comodel_records = Comodel.search_read(comodel_domain, field_names, limit=limit)
            if limit and len(comodel_records) == limit:
                return {'error_msg': str(SEARCH_PANEL_ERROR_MESSAGE)}

            field_range = []
            for record in comodel_records:
                record_id = record['id']
                values= {
                    'id': record_id,
                    'display_name': record['display_name'],
                }

                if group_by:
                    group_id, group_name = group_id_name(record[group_by])
                    values['group_id'] = group_id
                    values['group_name'] = group_name

                if enable_counters:
                    image_element = domain_image.get(record_id)
                    values['__count'] = image_element['__count'] if image_element else 0

                field_range.append(values)

            return { 'values': field_range, }

    def onchange(self, values: dict, field_names: list[str], fields_spec: dict):
        """
        Perform an onchange on the given fields, and return the result.

        :param values: dictionary mapping field names to values on the form view,
            giving the current state of modification
        :param field_names: names of the modified fields
        :param fields_spec: dictionary specifying the fields in the view,
            just like the one used by :meth:`web_read`; it is used to format
            the resulting values

        When creating a record from scratch, the client should call this with an
        empty list as ``field_names``. In that case, the method first adds
        default values to ``values``, computes the remaining fields, applies
        onchange methods to them, and return all the fields in ``fields_spec``.

        The result is a dictionary with two optional keys. The key ``"value"``
        is used to return field values that should be modified on the caller.
        The corresponding value is a dict mapping field names to their value,
        in the format of :meth:`web_read`, except for x2many fields, where the
        value is a list of commands to be applied on the caller's field value.

        The key ``"warning"`` provides a warning message to the caller. The
        corresponding value is a dictionary like::

            {
                "title": "Be careful!",         # subject of message
                "message": "Blah blah blah.",   # full warning message
                "type": "dialog",               # how to display the warning
            }

        """
        # this is for tests using `Form`
        self.env.flush_all()

        env = self.env
        first_call = not field_names

        if not (self and self._name == 'res.users'):
            # res.users defines SELF_WRITEABLE_FIELDS to give access to the user
            # to modify themselves, we skip the check in that case because the
            # user does not have write permission on themselves
            # TODO update res.users
            self.check_access('write' if self else 'create')

        if any(fname not in self._fields for fname in field_names):
            return {}

        if first_call:
            field_names = [fname for fname in values if fname != 'id']
            missing_names = [fname for fname in fields_spec if fname not in values]
            defaults = self.default_get(missing_names)
            for field_name in missing_names:
                if field_name in defaults:
                    values[field_name] = defaults[field_name]
                    field_names.append(field_name)
                else:
                    field = self._fields[field_name]
                    if not field.compute or self.pool.field_depends[field]:
                        # don't assign computed fields without dependencies,
                        # otherwise they don't get computed
                        values[field_name] = False

        # prefetch x2many lines: this speeds up the initial snapshot by avoiding
        # computing fields on new records as much as possible, as that can be
        # costly and is not necessary at all
        self.fetch(fields_spec.keys())
        for field_name, field_spec in fields_spec.items():
            field = self._fields[field_name]
            if field.type not in ('one2many', 'many2many'):
                continue
            sub_fields_spec = field_spec.get('fields') or {}
            if sub_fields_spec and values.get(field_name):
                # retrieve all line ids in commands
                line_ids = OrderedSet(self[field_name].ids)
                for cmd in values[field_name]:
                    if cmd[0] in (Command.UPDATE, Command.LINK):
                        line_ids.add(cmd[1])
                    elif cmd[0] == Command.SET:
                        line_ids.update(cmd[2])
                # prefetch stored fields on lines
                lines = self[field_name].browse(line_ids)
                lines.fetch(sub_fields_spec.keys())
                # copy the cache of lines to their corresponding new records;
                # this avoids computing computed stored fields on new_lines
                new_lines = lines.browse(map(NewId, line_ids))
                for field_name in sub_fields_spec:
                    field = lines._fields[field_name]
                    for new_line, line in zip(new_lines, lines):
                        line_value = field.convert_to_cache(line[field_name], new_line, validate=False)
                        field._update_cache(new_line, line_value)

        # Isolate changed values, to handle inconsistent data sent from the
        # client side: when a form view contains two one2many fields that
        # overlap, the lines that appear in both fields may be sent with
        # different data. Consider, for instance:
        #
        #   foo_ids: [line with value=1, ...]
        #   bar_ids: [line with value=1, ...]
        #
        # If value=2 is set on 'line' in 'bar_ids', the client sends
        #
        #   foo_ids: [line with value=1, ...]
        #   bar_ids: [line with value=2, ...]
        #
        # The idea is to put 'foo_ids' in cache first, so that the snapshot
        # contains value=1 for line in 'foo_ids'. The snapshot is then updated
        # with the value of `bar_ids`, which will contain value=2 on line.
        #
        # The issue also occurs with other fields. For instance, an onchange on
        # a move line has a value for the field 'move_id' that contains the
        # values of the move, among which the one2many that contains the line
        # itself, with old values!
        #
        initial_values = dict(values)
        changed_values = {fname: initial_values.pop(fname) for fname in field_names}

        # do not force delegate fields to False
        for parent_name in self._inherits.values():
            if not initial_values.get(parent_name, True):
                initial_values.pop(parent_name)

        # create a new record with initial values
        if self:
            # fill in the cache of record with the values of self
            cache_values = {fname: self[fname] for fname in fields_spec}
            record = self.new(cache_values, origin=self)
            # apply initial values on top of the values of self
            record._update_cache(initial_values)
        else:
            # set changed values to null in initial_values; not setting them
            # triggers default_get() on the new record when creating snapshot0
            initial_values.update(dict.fromkeys(field_names, False))
            record = self.new(initial_values)

        # make parent records match with the form values; this ensures that
        # computed fields on parent records have all their dependencies at
        # their expected value
        for field_name in initial_values:
            field = self._fields.get(field_name)
            if field and field.inherited:
                parent_name, field_name = field.related.split('.', 1)
                if parent := record[parent_name]:
                    parent._update_cache({field_name: record[field_name]})

        # make a snapshot based on the initial values of record
        snapshot0 = RecordSnapshot(record, fields_spec, fetch=(not first_call))

        # store changed values in cache; also trigger recomputations based on
        # subfields (e.g., line.a has been modified, line.b is computed stored
        # and depends on line.a, but line.b is not in the form view)
        record._update_cache(changed_values)

        # update snapshot0 with changed values
        for field_name in field_names:
            snapshot0.fetch(field_name)

        # Determine which field(s) should be triggered an onchange. On the first
        # call, 'names' only contains fields with a default. If 'self' is a new
        # line in a one2many field, 'names' also contains the one2many's inverse
        # field, and that field may not be in nametree.
        todo = list(unique(itertools.chain(field_names, fields_spec))) if first_call else list(field_names)
        done = set()

        # mark fields to do as modified to trigger recomputations
        protected = [
            field
            for mod_field in [self._fields[fname] for fname in field_names]
            for field in self.pool.field_computed.get(mod_field) or [mod_field]
        ]
        with self.env.protecting(protected, record):
            record.modified(list(self._fields) if first_call else todo)
            for field_name in todo:
                field = self._fields[field_name]
                if field.inherited:
                    # modifying an inherited field should modify the parent
                    # record accordingly; because we don't actually assign the
                    # modified field on the record, the modification on the
                    # parent record has to be done explicitly
                    parent = record[field.related.split('.')[0]]
                    parent[field_name] = record[field_name]

        result = {'warnings': OrderedSet()}

        # process names in order
        while todo:
            # apply field-specific onchange methods
            for field_name in todo:
                record._apply_onchange_methods(field_name, result)
                done.add(field_name)

            if not env.context.get('recursive_onchanges', True):
                break

            # determine which fields to process for the next pass
            todo = [
                field_name
                for field_name in fields_spec
                if field_name not in done and snapshot0.has_changed(field_name)
            ]

        # make the snapshot with the final values of record
        snapshot1 = RecordSnapshot(record, fields_spec)

        # determine values that have changed by comparing snapshots
        result['value'] = snapshot1.diff(snapshot0, force=first_call)

        # format warnings
        warnings = result.pop('warnings')
        if len(warnings) == 1:
            title, message, type_ = warnings.pop()
            if not type_:
                type_ = 'dialog'
            result['warning'] = dict(title=title, message=message, type=type_)
        elif len(warnings) > 1:
            # concatenate warning titles and messages
            title = self.env._("Warnings")
            message = '\n\n'.join([warn_title + '\n\n' + warn_message for warn_title, warn_message, warn_type in warnings])
            result['warning'] = dict(title=title, message=message, type='dialog')

        return result

    def web_override_translations(self, values):
        """
        This method is used to override all the modal translations of the given fields
        with the provided value for each field.

        :param values: dictionary of the translations to apply for each field name
            ex: ``{ "field_name": "new_value" }``
        """
        self.ensure_one()
        for field_name in values:
            field = self._fields[field_name]
            if field.translate is True:
                translations = {lang: False for lang, _ in self.env['res.lang'].get_installed()}
                translations['en_US'] = values[field_name]
                translations[self.env.lang or 'en_US'] = values[field_name]
                self.update_field_translations(field_name, translations)


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        style_fields = {'external_report_layout_id', 'font', 'primary_color', 'secondary_color'}
        if any(not style_fields.isdisjoint(values) for values in vals_list):
            self._update_asset_style()
        return companies

    def write(self, vals):
        res = super().write(vals)
        style_fields = {'external_report_layout_id', 'font', 'primary_color', 'secondary_color'}
        if not style_fields.isdisjoint(vals):
            self._update_asset_style()
        return res

    def _get_asset_style_b64(self):
        # One bundle for everyone, so this method
        # necessarily updates the style for every company at once
        company_ids = self.sudo().search([])
        company_styles = self.env['ir.qweb']._render('web.styles_company_report', {
                'company_ids': company_ids,
            }, raise_if_not_found=False)
        return base64.b64encode(company_styles.encode())

    def _update_asset_style(self):
        asset_attachment = self.env.ref('web.asset_styles_company_report', raise_if_not_found=False)
        if not asset_attachment:
            return
        asset_attachment = asset_attachment.sudo()
        b64_val = self._get_asset_style_b64()
        if b64_val != asset_attachment.datas:
            asset_attachment.write({'datas': b64_val})


class RecordSnapshot(dict):
    """ A dict with the values of a record, following a prefix tree. """
    __slots__ = ['record', 'fields_spec']

    def __init__(self, record: BaseModel, fields_spec: dict, fetch=True):
        # put record in dict to include it when comparing snapshots
        super().__init__()
        self.record = record
        self.fields_spec = fields_spec
        if fetch:
            for name in fields_spec:
                self.fetch(name)

    def __eq__(self, other: 'RecordSnapshot'):
        return self.record == other.record and super().__eq__(other)

    def fetch(self, field_name):
        """ Set the value of field ``name`` from the record's value. """
        if self.record._fields[field_name].type in ('one2many', 'many2many'):
            # x2many fields are serialized as a dict of line snapshots
            lines = self.record[field_name]
            if 'context' in self.fields_spec[field_name]:
                lines = lines.with_context(**self.fields_spec[field_name]['context'])
            sub_fields_spec = self.fields_spec[field_name].get('fields') or {}
            self[field_name] = {line.id: RecordSnapshot(line, sub_fields_spec) for line in lines}
        else:
            self[field_name] = self.record[field_name]

    def has_changed(self, field_name) -> bool:
        """ Return whether a field on the record has changed. """
        if field_name not in self:
            return True
        if self.record._fields[field_name].type not in ('one2many', 'many2many'):
            return self[field_name] != self.record[field_name]
        return self[field_name].keys() != set(self.record[field_name]._ids) or any(
            line_snapshot.has_changed(subname)
            for line_snapshot in self[field_name].values()
            for subname in self.fields_spec[field_name].get('fields') or {}
        )

    def diff(self, other: 'RecordSnapshot', force=False):
        """ Return the values in ``self`` that differ from ``other``. """

        # determine fields to return
        simple_fields_spec = {}
        x2many_fields_spec = {}
        for field_name, field_spec in self.fields_spec.items():
            if field_name == 'id':
                continue
            if not force and other.get(field_name) == self[field_name]:
                continue
            field = self.record._fields[field_name]
            if field.type in ('one2many', 'many2many'):
                x2many_fields_spec[field_name] = field_spec
            else:
                simple_fields_spec[field_name] = field_spec

        # use web_read() for simple fields
        [result] = self.record.web_read(simple_fields_spec)

        # discard the NewId from the dict
        result.pop('id')

        # for x2many fields: serialize value as commands
        for field_name, field_spec in x2many_fields_spec.items():
            commands = []

            self_value = self[field_name]
            other_value = {} if force else other.get(field_name) or {}
            if any(other_value):
                # other may be a snapshot for a real record, adapt its x2many ids
                other_value = {NewId(id_): snap for id_, snap in other_value.items()}

            # commands for removed lines
            field = self.record._fields[field_name]
            remove = Command.delete if field.type == 'one2many' else Command.unlink
            for id_ in other_value:
                if id_ not in self_value:
                    commands.append(remove(id_.origin or id_.ref or 0))

            # commands for modified or extra lines
            for id_, line_snapshot in self_value.items():
                if not force and id_ in other_value:
                    # existing line: check diff and send update
                    line_diff = line_snapshot.diff(other_value[id_])
                    if line_diff:
                        commands.append(Command.update(id_.origin or id_.ref or 0, line_diff))

                elif not id_.origin:
                    # new line: send diff from scratch
                    line_diff = line_snapshot.diff({})
                    commands.append((Command.CREATE, id_.origin or id_.ref or 0, line_diff))

                else:
                    # link line: send data to client
                    base_line = line_snapshot.record._origin
                    [base_data] = base_line.web_read(field_spec.get('fields') or {})
                    commands.append((Command.LINK, base_line.id, base_data))

                    # check diff and send update
                    base_snapshot = RecordSnapshot(base_line, field_spec.get('fields') or {})
                    line_diff = line_snapshot.diff(base_snapshot)
                    if line_diff:
                        commands.append(Command.update(id_.origin, line_diff))

            if commands:
                result[field_name] = commands

        return result
