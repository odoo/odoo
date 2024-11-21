# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import itertools
import json

from odoo import api, models
from odoo.fields import Command
from odoo.models import BaseModel, NewId
from odoo.osv.expression import AND, TRUE_DOMAIN, normalize_domain
from odoo.tools import unique, OrderedSet
from odoo.exceptions import AccessError, UserError
from collections import defaultdict
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)
SEARCH_PANEL_ERROR_MESSAGE = _lt("Too many items to display.")

def is_true_domain(domain):
    return normalize_domain(domain) == TRUE_DOMAIN


class lazymapping(defaultdict):
    def __missing__(self, key):
        value = self.default_factory(key)
        self[key] = value
        return value

DISPLAY_DATE_FORMATS = {
    'day': 'dd MMM yyyy',
    'week': "'W'w YYYY",
    'month': 'MMMM yyyy',
    'quarter': 'QQQ yyyy',
    'year': 'yyyy',
}


class Base(models.AbstractModel):
    _inherit = 'base'

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
        force_search_count = self._context.get('force_search_count')
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
                    co_records = co_records.search([('id', 'in', co_records.ids)], order=field_spec['order'])
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

                    if field.type == 'reference':
                        co_record = record[field_name]
                    else:  # field.type == 'many2one_reference'
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

                    record_values = values_by_id[record.id]

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

        return values_list

    @api.model
    @api.readonly
    def web_read_group(self, domain, fields, groupby, limit=None, offset=0, orderby=False, lazy=True):
        """
        Returns the result of a read_group and the total number of groups matching the search domain.

        :param domain: search domain
        :param fields: list of fields to read (see ``fields``` param of ``read_group``)
        :param groupby: list of fields to group on (see ``groupby``` param of ``read_group``)
        :param limit: see ``limit`` param of ``read_group``
        :param offset: see ``offset`` param of ``read_group``
        :param orderby: see ``orderby`` param of ``read_group``
        :param lazy: see ``lazy`` param of ``read_group``
        :return: {
            'groups': array of read groups
            'length': total number of groups
        }
        """
        groups = self._web_read_group(domain, fields, groupby, limit, offset, orderby, lazy)

        if not groups:
            length = 0
        elif limit and len(groups) == limit:
            annotated_groupby = self._read_group_get_annotated_groupby(groupby, lazy=lazy)
            length = limit + len(self._read_group(
                domain,
                groupby=annotated_groupby.values(),
                offset=limit,
            ))

        else:
            length = len(groups) + offset
        return {
            'groups': groups,
            'length': length
        }

    @api.model
    def _web_read_group(self, domain, fields, groupby, limit=None, offset=0, orderby=False, lazy=True):
        """
        See ``web_read_group`` for params description.

        :returns: array of groups
        """
        groups = self.read_group(domain, fields, groupby, offset=offset, limit=limit,
                                 orderby=orderby, lazy=lazy)
        return groups

    @api.model
    @api.readonly
    def read_progress_bar(self, domain, group_by, progress_bar):
        """
        Gets the data needed for all the kanban column progressbars.
        These are fetched alongside read_group operation.

        :param domain - the domain used in the kanban view to filter records
        :param group_by - the name of the field used to group records into
                        kanban columns
        :param progress_bar - the <progressbar/> declaration attributes
                            (field, colors, sum)
        :return a dictionnary mapping group_by values to dictionnaries mapping
                progress bar field values to the related number of records
        """
        def adapt(value):
            if isinstance(value, tuple):
                value = value[0]
            return value

        result = {}
        for group in self.read_group(domain, ['__count'], [group_by, progress_bar['field']], lazy=False):
            group_by_value = str(adapt(group[group_by]))
            field_value = group[progress_bar['field']]
            if group_by_value not in result:
                result[group_by_value] = dict.fromkeys(progress_bar['colors'], 0)
            if field_value in result[group_by_value]:
                result[group_by_value][field_value] += group['__count']
        return result

    @api.model
    def _search_panel_field_image(self, field_name, **kwargs):
        """
        Return the values in the image of the provided domain by field_name.

        :param model_domain: domain whose image is returned
        :param extra_domain: extra domain to use when counting records associated with field values
        :param field_name: the name of a field (type many2one or selection)
        :param enable_counters: whether to set the key '__count' in image values
        :param only_counters: whether to retrieve information on the model_domain image or only
                                counts based on model_domain and extra_domain. In the later case,
                                the counts are set whatever is enable_counters.
        :param limit: integer, maximal number of values to fetch
        :param set_limit: boolean, whether to use the provided limit (if any)
        :return: a dict of the form
                    {
                        id: { 'id': id, 'display_name': display_name, ('__count': c,) },
                        ...
                    }
        """

        enable_counters = kwargs.get('enable_counters')
        only_counters = kwargs.get('only_counters')
        extra_domain = kwargs.get('extra_domain', [])
        no_extra = is_true_domain(extra_domain)
        model_domain = kwargs.get('model_domain', [])
        count_domain = AND([model_domain, extra_domain])

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
        :return: a dict of the form
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
            desc = self.fields_get([field_name])[field_name]
            field_name_selection = dict(desc['selection'])

            def group_id_name(value):
                return value, field_name_selection[value]

        domain = AND([
            domain,
            [(field_name, '!=', False)],
        ])
        groups = self.read_group(domain, [field_name], [field_name], limit=limit)

        domain_image = {}
        for group in groups:
            id, display_name = group_id_name(group[field_name])
            values = {
                'id': id,
                'display_name': display_name,
            }
            if set_count:
                values['__count'] = group[field_name + '_count']
            domain_image[id] = values

        return domain_image


    @api.model
    def _search_panel_global_counters(self, values_range, parent_name):
        """
        Modify in place values_range to transform the (local) counts
        into global counts (local count + children local counts)
        in case a parent field parent_name has been set on the range values.
        Note that we save the initial (local) counts into an auxiliary dict
        before they could be changed in the for loop below.

        :param values_range: dict of the form
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
                (if ids = records.ids, that condition is automatically satisfied)
            3) it is maximal among other sublists with properties 1 and 2.

        :param records, the list of records to filter, the records must have the form
                        { 'id': id, parent_name: False or (id, display_name),... }
        :param parent_name, string, indicates which key determines the parent
        :param ids: list of record ids
        :return: the sublist of records with the above properties
        }
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
                if known_status != None:
                    # the record and its known ancestors have already been considered
                    chain_is_fully_included = known_status
                    break
                record = allowed_records.get(record_id)
                if record:
                    ancestor_chain[record_id] = record
                    record_id = get_parent_id(record)
                else:
                    chain_is_fully_included = False

            for id, record in ancestor_chain.items():
                records_to_keep[id] = chain_is_fully_included

        # we keep initial order
        return [rec for rec in records if records_to_keep.get(rec['id'])]


    @api.model
    def _search_panel_selection_range(self, field_name, **kwargs):
        """
        Return the values of a field of type selection possibly enriched
        with counts of associated records in domain.

        :param enable_counters: whether to set the key '__count' on values returned.
                                    Default is False.
        :param expand: whether to return the full range of values for the selection
                        field or only the field image values. Default is False.
        :param field_name: the name of a field of type selection
        :param model_domain: domain used to determine the field image values and counts.
                                Default is [].
        :return: a list of dicts of the form
                    { 'id': id, 'display_name': display_name, ('__count': c,) }
                with key '__count' set if enable_counters is True
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

        :param field_name: the name of a field;
            of type many2one or selection.
        :param category_domain: domain generated by categories. Default is [].
        :param comodel_domain: domain of field values (if relational). Default is [].
        :param enable_counters: whether to count records by value. Default is False.
        :param expand: whether to return the full range of field values in comodel_domain
                        or only the field image values (possibly filtered and/or completed
                        with parents if hierarchize is set). Default is False.
        :param filter_domain: domain generated by filters. Default is [].
        :param hierarchize: determines if the categories must be displayed hierarchically
                            (if possible). If set to true and _parent_name is set on the
                            comodel field, the information necessary for the hierarchization will
                            be returned. Default is True.
        :param limit: integer, maximal number of values to fetch. Default is None.
        :param search_domain: base domain of search. Default is [].
                        with parents if hierarchize is set)
        :return: {
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
        :param category_domain: domain generated by categories. Default is [].
        :param comodel_domain: domain of field values (if relational)
                                (this parameter is used in _search_panel_range). Default is [].
        :param enable_counters: whether to count records by value. Default is False.
        :param expand: whether to return the full range of field values in comodel_domain
                        or only the field image values. Default is False.
        :param filter_domain: domain generated by filters. Default is [].
        :param group_by: extra field to read on comodel, to group comodel records
        :param group_domain: dict, one domain for each activated group
                                for the group_by (if any). Those domains are
                                used to fech accurate counters for values in each group.
                                Default is [] (many2one case) or None.
        :param limit: integer, maximal number of values to fetch. Default is None.
        :param search_domain: base domain of search. Default is [].
        :return: {
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
        cache = env.cache
        first_call = not field_names

        if any(fname not in self._fields for fname in field_names):
            return {}

        if first_call:
            field_names = [fname for fname in values if fname != 'id']
            missing_names = [fname for fname in fields_spec if fname not in values]
            defaults = self.default_get(missing_names)
            for field_name in missing_names:
                values[field_name] = defaults.get(field_name, False)
                if field_name in defaults:
                    field_names.append(field_name)

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
                    line_values = [
                        field.convert_to_cache(line[field_name], new_line, validate=False)
                        for new_line, line in zip(new_lines, lines)
                    ]
                    cache.update(new_lines, field, line_values)

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
            record = self.new(initial_values, origin=self)

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
            record.modified(todo)
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
        ex: { "field_name": "new_value" }
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

    def write(self, values):
        res = super().write(values)
        style_fields = {'external_report_layout_id', 'font', 'primary_color', 'secondary_color'}
        if not style_fields.isdisjoint(values):
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
