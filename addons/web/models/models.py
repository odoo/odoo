# -*- coding: utf-8 -*-
import babel.dates
import pytz
from lxml import etree
import base64
import json

from odoo import _, _lt, api, fields, models
from odoo.osv.expression import AND, TRUE_DOMAIN, normalize_domain
from odoo.tools import lazy
from odoo.tools.misc import get_lang
from odoo.exceptions import UserError
from collections import defaultdict

SEARCH_PANEL_ERROR_MESSAGE = _lt("Too many items to display.")

def is_true_domain(domain):
    return normalize_domain(domain) == TRUE_DOMAIN


class lazymapping(defaultdict):
    def __missing__(self, key):
        value = self.default_factory(key)
        self[key] = value
        return value

class IrActionsActWindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=[
        ('qweb', 'QWeb')
    ], ondelete={'qweb': 'cascade'})


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def web_search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """
        Performs a search_read and a search_count.

        :param domain: search domain
        :param fields: list of fields to read
        :param limit: maximum number of records to read
        :param offset: number of records to skip
        :param order: columns to sort results
        :return: {
            'records': array of read records (result of a call to 'search_read')
            'length': number of records matching the domain (result of a call to 'search_count')
        }
        """
        records = self.search_read(domain, fields, offset=offset, limit=limit, order=order)
        if not records:
            return {
                'length': 0,
                'records': []
            }
        if limit and (len(records) == limit or self.env.context.get('force_search_count')):
            length = self.search_count(domain)
        else:
            length = len(records) + offset
        return {
            'length': length,
            'records': records
        }

    @api.model
    def web_read_group(self, domain, fields, groupby, limit=None, offset=0, orderby=False,
                       lazy=True, expand=False, expand_limit=None, expand_orderby=False):
        """
        Returns the result of a read_group (and optionally search for and read records inside each
        group), and the total number of groups matching the search domain.

        :param domain: search domain
        :param fields: list of fields to read (see ``fields``` param of ``read_group``)
        :param groupby: list of fields to group on (see ``groupby``` param of ``read_group``)
        :param limit: see ``limit`` param of ``read_group``
        :param offset: see ``offset`` param of ``read_group``
        :param orderby: see ``orderby`` param of ``read_group``
        :param lazy: see ``lazy`` param of ``read_group``
        :param expand: if true, and groupby only contains one field, read records inside each group
        :param expand_limit: maximum number of records to read in each group
        :param expand_orderby: order to apply when reading records in each group
        :return: {
            'groups': array of read groups
            'length': total number of groups
        }
        """
        groups = self._web_read_group(domain, fields, groupby, limit, offset, orderby, lazy, expand,
                                      expand_limit, expand_orderby)

        if not groups:
            length = 0
        elif limit and len(groups) == limit:
            all_groups = self.read_group(domain, ['display_name'], groupby, lazy=True)
            length = len(all_groups)
        else:
            length = len(groups) + offset
        return {
            'groups': groups,
            'length': length
        }

    @api.model
    def _web_read_group(self, domain, fields, groupby, limit=None, offset=0, orderby=False,
                        lazy=True, expand=False, expand_limit=None, expand_orderby=False):
        """
        Performs a read_group and optionally a web_search_read for each group.
        See ``web_read_group`` for params description.

        :returns: array of groups
        """
        groups = self.read_group(domain, fields, groupby, offset=offset, limit=limit,
                                 orderby=orderby, lazy=lazy)

        if expand and len(groupby) == 1:
            for group in groups:
                group['__data'] = self.web_search_read(domain=group['__domain'], fields=fields,
                                                       offset=0, limit=expand_limit,
                                                       order=expand_orderby)

        return groups

    @api.model
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

        # Workaround to match read_group's infrastructure
        # TO DO in master: harmonize this function and readgroup to allow factorization
        group_by_modifier = group_by.partition(':')[2] or 'month'
        group_by = group_by.partition(':')[0]
        display_date_formats = {
            'day': 'dd MMM yyyy',
            'week': "'W'w YYYY",
            'month': 'MMMM yyyy',
            'quarter': 'QQQ yyyy',
            'year': 'yyyy'}

        records_values = self.search_read(domain or [], [progress_bar['field'], group_by])

        data = {}
        field_type = self._fields[group_by].type
        if field_type == 'selection':
            selection_labels = dict(self.fields_get()[group_by]['selection'])

        for record_values in records_values:
            group_by_value = record_values[group_by]

            # Again, imitating what _read_group_format_result and _read_group_prepare_data do
            if group_by_value and field_type in ['date', 'datetime']:
                locale = get_lang(self.env).code
                group_by_value = fields.Datetime.to_datetime(group_by_value)
                group_by_value = pytz.timezone('UTC').localize(group_by_value)
                tz_info = None
                if field_type == 'datetime' and self._context.get('tz') in pytz.all_timezones:
                    tz_info = self._context.get('tz')
                    group_by_value = babel.dates.format_datetime(
                        group_by_value, format=display_date_formats[group_by_modifier],
                        tzinfo=tz_info, locale=locale)
                else:
                    group_by_value = babel.dates.format_date(
                        group_by_value, format=display_date_formats[group_by_modifier],
                        locale=locale)

            if field_type == 'selection':
                group_by_value = selection_labels[group_by_value] \
                    if group_by_value in selection_labels else False

            if type(group_by_value) == tuple:
                group_by_value = group_by_value[1] # FIXME should use technical value (0)

            if group_by_value not in data:
                data[group_by_value] = {}
                for key in progress_bar['colors']:
                    data[group_by_value][key] = 0

            field_value = record_values[progress_bar['field']]
            if field_value in data[group_by_value]:
                data[group_by_value][field_value] += 1

        return data

    ##### qweb view hooks #####
    @api.model
    def qweb_render_view(self, view_id, domain):
        assert view_id
        return self.env['ir.qweb']._render(
            view_id, {
            **self.env['ir.ui.view']._prepare_qcontext(),
            **self._qweb_prepare_qcontext(view_id, domain),
        })

    def _qweb_prepare_qcontext(self, view_id, domain):
        """
        Base qcontext for rendering qweb views bound to this model
        """
        return {
            'model': self,
            'domain': domain,
            # not necessarily necessary as env is already part of the
            # non-minimal qcontext
            'context': self.env.context,
            'records': lazy(self.search, domain),
        }

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        r = super().fields_view_get(view_id, view_type, toolbar, submenu)
        # avoid leaking the raw (un-rendered) template, also avoids bloating
        # the response payload for no reason. Only send the root node,
        # to send attributes such as `js_class`.
        if r['type'] == 'qweb':
            root = etree.fromstring(r['arch'])
            r['arch'] = etree.tostring(etree.Element('qweb', root.attrib))
        return r

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
        if field.type == 'many2one':
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
            raise UserError(_(
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
            raise UserError(_('Only types %(supported_types)s are supported for filter (found type %(field_type)s)',
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
                    return value or (False, _("Not Set"))

            elif group_by_field.type == 'selection':
                desc = Comodel.fields_get([group_by])[group_by]
                group_by_selection = dict(desc['selection'])
                group_by_selection[False] = _("Not Set")

                def group_id_name(value):
                    return value, group_by_selection[value]

            else:
                def group_id_name(value):
                    return (value, value) if value else (False, _("Not Set"))

        comodel_domain = kwargs.get('comodel_domain', [])
        enable_counters = kwargs.get('enable_counters')
        expand = kwargs.get('expand')

        if field.type == 'many2many':
            comodel_records = Comodel.search_read(comodel_domain, field_names, limit=limit)
            if expand and limit and len(comodel_records) == limit:
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

                if enable_counters or not expand:
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
                    if enable_counters:
                        count = self.search_count(search_count_domain)
                    if not expand:
                        if enable_counters and is_true_domain(local_extra_domain):
                            inImage = count
                        else:
                            inImage = self.search(search_domain, limit=1)

                if expand or inImage:
                    if enable_counters:
                        values['__count'] = count
                    field_range.append(values)

            if not expand and limit and len(field_range) == limit:
                return {'error_msg': str(SEARCH_PANEL_ERROR_MESSAGE)}

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


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def create(self, values):
        res = super().create(values)
        style_fields = {'external_report_layout_id', 'font', 'primary_color', 'secondary_color'}
        if not style_fields.isdisjoint(values):
            self._update_asset_style()
        return res

    def write(self, values):
        res = super().write(values)
        style_fields = {'external_report_layout_id', 'font', 'primary_color', 'secondary_color'}
        if not style_fields.isdisjoint(values):
            self._update_asset_style()
        return res

    def _get_asset_style_b64(self):
        template_style = self.env.ref('web.styles_company_report', raise_if_not_found=False)
        if not template_style:
            return b''
        # One bundle for everyone, so this method
        # necessarily updates the style for every company at once
        company_ids = self.sudo().search([])
        company_styles = template_style._render({
            'company_ids': company_ids,
        })
        return base64.b64encode((company_styles))

    def _update_asset_style(self):
        asset_attachment = self.env.ref('web.asset_styles_company_report', raise_if_not_found=False)
        if not asset_attachment:
            return
        asset_attachment = asset_attachment.sudo()
        b64_val = self._get_asset_style_b64()
        if b64_val != asset_attachment.datas:
            asset_attachment.write({'datas': b64_val})
