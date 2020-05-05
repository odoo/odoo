# -*- coding: utf-8 -*-
import babel.dates
import pytz
from lxml import etree
import base64
import json

from odoo import _, api, fields, models
from odoo.osv.expression import AND
from odoo.tools import lazy
from odoo.tools.misc import get_lang
from odoo.exceptions import UserError
from collections import defaultdict

SEARCH_PANEL_LIMIT = 200

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
        return self.env['ir.qweb'].render(
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
    def search_panel_local_counters(self, field_name, **kwargs):
        """
        Return the record counts associated with the field_name values.

        :param field_name: the name of a field (type many2one or selection)
        :param category_domain: domain generated by categories
        :param filter_domain: domain generated by filters
        :param group_domain: domain generated by the field_name active values
                                if field_name is used as a filter
        :param search_domain: base domain of search
        :return: a dict of the form {id: c,... } where id is a field_name value
                    and c is the associated record count
        """
        count_domain = AND([
            kwargs.get('search_domain', []),
            kwargs.get('category_domain', []),
            kwargs.get('filter_domain', []),
            kwargs.get('group_domain', []),
            [(field_name, '!=', False)]
        ])

        field = self._fields[field_name]

        if field.type == 'many2one':
            def get_group_id(group):
                return group[field_name][0]

        else:
            # field type is selection: see doc above
            def get_group_id(group):
                return group[field_name]

        groups = self.read_group(count_domain, [field_name], [field_name])
        local_counters = {}
        for group in groups:
            group_id = get_group_id(group)
            local_counters[group_id] = group[field_name + '_count']

        return local_counters


    @api.model
    def search_panel_global_counters(self, values_range, parent_name):
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
    def _search_panel_range(self, field_name, **kwargs):
        """
        Return possible values of the field field_name,
        possibly with counters and other info (if the extra parameter
        comodel_field_names has been provided).

        :param field_name: the name of a filter field;
            possible types are many2one, many2many, selection.
        :param category_domain: domain generated by categories
                                (this parameter is used in search_panel_local_counters)
        :param comodel_domain: domain of field values (if relational)
                                (this parameter is used in search_panel_local_counters)
        :param comodel_field_names: a dict with keys given by field names of the comodel
                                    of field_name (if relational).
                                    the values are functions used to process
                                    the field names values. They must accept the single
                                    parameter record (see below)
        :param disable_counters: whether to count records by value. This is done in
                                    search_panel_local_counters
        :param filter_domain: domain generated by filters
                                (this parameter is used in search_panel_local_counters)
        :param search_domain: base domain of search
                                (this parameter is used in search_panel_local_counters)
        :return: a list of possible values, each being a dict with keys
            'id' (value),
            'name' (value label),
            '__count' (how many records with that value),
            and possibly other keys
        """
        field = self._fields[field_name]

        local_counters = {}
        if field.type != 'many2many' and not kwargs.get('disable_counters'):
            local_counters = self.search_panel_local_counters(field_name, **kwargs)

        if field.type in ['many2many', 'many2one']:
            Comodel = self.env[field.comodel_name]
            comodel_domain = kwargs.get('comodel_domain', [])
            field_names = kwargs.get('comodel_field_names', {})
            # we fetch display_name but do not not process it
            field_names['display_name'] = lambda record: None

            records = Comodel.with_context(hierarchical_naming=False).search_read(comodel_domain, field_names.keys(), limit=SEARCH_PANEL_LIMIT)

            values_range = {}
            for record in records:
                record_id = record['id']
                record['__count'] = local_counters.get(record_id, 0)
                for fn in field_names.values():
                    fn(record)
                values_range[record_id] = record
            return values_range

        if field.type == 'selection':
            selection = self.fields_get([field_name])[field_name]['selection']

            values_range = {}
            for value, label in selection:
                values_range[value] = {
                    'id': value,
                    'display_name': label,
                    '__count': local_counters.get(value, 0),
                }
            return values_range


    @api.model
    def search_panel_select_range(self, field_name, **kwargs):
        """
        Return possible values of the field field_name (case select="one"),
        possibly with counters and the parent field (if any) used to hierarchize them.

        :param field_name: the name of a field;
            of type many2one or selection.
        :param category_domain: domain generated by categories
                                (this parameter is used in _search_panel_range)
        :param comodel_domain: domain of field values (if relational)
                                (this parameter is used in _search_panel_range)
        :param disable_counters: whether to count records by value
        :param search_domain: base domain of search
                                (this parameter is used in _search_panel_range)
        :return: {
            'parent_field': parent field on the comodel of field, or False
            'values': array of dictionaries containing some info on the records
                        available on the comodel of the field 'field_name'.
                        The display name, the __count (how many records with that value)
                        and possibly parent_field are fetched.
        }
        """
        field = self._fields[field_name]
        supported_types = ['many2one', 'selection']
        if field.type not in supported_types:
            raise UserError(_('Only types %(supported_types)s are supported for category (found type %(field_type)s)') % ({
                            'supported_types': supported_types, 'field_type': field.type}))

        field_names = {}
        parent_name = False
        if field.type == 'many2one':
            Comodel = self.env[field.comodel_name]
            if Comodel._parent_name in Comodel._fields:
                parent_name = Comodel._parent_name

                def process_parent_field(record):
                    parent_id = record[parent_name]
                    if parent_id:
                        record[parent_name] = parent_id[0]

                field_names[parent_name] = process_parent_field

        values_range = self._search_panel_range(field_name, comodel_field_names=field_names, **kwargs)

        if parent_name and not kwargs.get('disable_counters') and len(values_range) < SEARCH_PANEL_LIMIT:
            self.search_panel_global_counters(values_range, parent_name)

        return {
            'parent_field': parent_name,
            'values': list(values_range.values()),
        }


    @api.model
    def search_panel_select_multi_range(self, field_name, **kwargs):
        """
        Return possible values of the field field_name (case select="multi"),
        possibly with counters and groups.

        :param field_name: the name of a filter field;
            possible types are many2one, many2many, selection.
        :param category_domain: domain generated by categories
        :param comodel_domain: domain of field values (if relational)
                                (this parameter is used in _search_panel_range)
        :param disable_counters: whether to count records by value
        :param filter_domain: domain generated by filters
        :param group_by: extra field to read on comodel, to group comodel records
        :param group_domain: dict, one domain for each activated group
                                for the group_by (if any). Those domains are
                                used to fech accurate counters for values in each group
        :param search_domain: base domain of search
        :return: a list of possible values, each being a dict with keys
            'id' (value),
            'name' (value label),
            '__count' (how many records with that value),
            'group_id' (value of group), set if a group_by has been provided,
            'group_name' (label of group), set if a group_by has been provided
        """
        field = self._fields[field_name]
        supported_types = ['many2one', 'many2many', 'selection']
        if field.type not in supported_types:
            raise UserError(_('Only types %(supported_types)s are supported for filter (found type %(field_type)s)') % ({
                            'supported_types': supported_types, 'field_type': field.type}))

        field_names = {}
        group_by = kwargs.get('group_by')
        if group_by and field.type != 'selection':
            # add group_by to the fields to fetch and tell
            # how to process its values
            Comodel = self.env.get(field.comodel_name)
            group_by_field = Comodel._fields[group_by]

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

            def process_groupby_field(record):
                value = record.pop(group_by)
                record['group_id'], record['group_name'] = group_id_name(value)

            field_names[group_by] = process_groupby_field

        values_range = self._search_panel_range(field_name, comodel_field_names=field_names, **kwargs)

        if field.type == 'many2many' and not kwargs.get('disable_counters'):
            # fetch the counts
            model_domain = AND([
                kwargs.get('search_domain', []),
                kwargs.get('category_domain', []),
                kwargs.get('filter_domain', []),
                [(field_name, '!=', False)]
            ])
            group_domain = kwargs.get('group_domain', {})
            for id in values_range:
                values = values_range[id]

                count_domain = AND([model_domain, [(field_name, 'in', id)], ])
                if group_by and group_domain:
                    group_id = json.dumps(values['group_id'])
                    extra_domain = group_domain.get(group_id, [])
                    count_domain = AND([count_domain, extra_domain, ])

                values['__count'] = self.search_count(count_domain)

        return list(values_range.values())


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def create(self, values):
        res = super().create(values)
        if 'primary_color' in values or 'secondary_color' in values or 'font' in values:
            self._update_asset_style()
        return res

    def write(self, values):
        res = super().write(values)
        if 'primary_color' in values or 'secondary_color' in values or 'font' in values:
            self._update_asset_style()
        return res

    def _get_asset_style_b64(self):
        template_style = self.env.ref('web.styles_company_report', raise_if_not_found=False)
        if not template_style:
            return b''
        # One bundle for everyone, so this method
        # necessarily updates the style for every company at once
        company_ids = self.sudo().search([])
        company_styles = template_style.render({
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
