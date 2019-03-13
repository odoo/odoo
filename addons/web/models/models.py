# -*- coding: utf-8 -*-
import babel.dates
import pytz

from odoo import _, api, fields, models
from odoo.osv.expression import AND
from odoo.tools import lazy
from odoo.exceptions import UserError


class IrActionsActWindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=[('qweb', 'QWeb')])


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def web_read_group(self, domain, fields, groupby, limit=None, offset=0, orderby=False,
                       lazy=True):
        """
        Returns the result of a read_group and the total number of groups matching the search
        domain.

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
        groups = self.read_group(domain, fields, groupby, offset=offset, limit=limit,
                                 orderby=orderby, lazy=lazy)

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
                locale = self._context.get('lang') or 'en_US'
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
        # the response payload for no reason
        if r['type'] == 'qweb':
            r['arch'] = '<qweb/>'
        return r

    @api.model
    def search_panel_select_range(self, field_name):
        """
        Return possible values of the field field_name (case select="one")
        and the parent field (if any) used to hierarchize them.

        :param field_name: the name of a many2one category field
        :return: {
            'parent_field': parent field on the comodel of field, or False
            'values': array of dictionaries containing some info on the records
                        available on the comodel of the field 'field_name'.
                        The display name (and possibly parent_field) are fetched.
        }
        """
        field = self._fields[field_name]
        supported_types = ['many2one']
        if field.type not in supported_types:
            raise UserError(_('Only types %(supported_types)s are supported for category (found type %(field_type)s)') % ({
                            'supported_types': supported_types, 'field_type': field.type}))

        Comodel = self.env[field.comodel_name]
        fields = ['display_name']
        parent_name = Comodel._parent_name if Comodel._parent_name in Comodel._fields else False
        if parent_name:
            fields.append(parent_name)
        return {
            'parent_field': parent_name,
            'values': Comodel.with_context(hierarchical_naming=False).search_read([], fields),
        }

    @api.model
    def search_panel_select_multi_range(self, field_name, **kwargs):
        """
        Return possible values of the field field_name (case select="multi"),
        possibly with counters and groups.

        :param field_name: the name of a filter field;
            possible types are many2one, many2many, selection.
        :param search_domain: base domain of search
        :param category_domain: domain generated by categories
        :param filter_domain: domain generated by filters
        :param comodel_domain: domain of field values (if relational)
        :param group_by: extra field to read on comodel, to group comodel records
        :param disable_counters: whether to count records by value
        :return: a list of possible values, each being a dict with keys
            'id' (value),
            'name' (value label),
            'count' (how many records with that value),
            'group_id' (value of group),
            'group_name' (label of group).
        """
        field = self._fields[field_name]
        supported_types = ['many2one', 'many2many', 'selection']
        if field.type not in supported_types:
            raise UserError(_('Only types %(supported_types)s are supported for filter (found type %(field_type)s)') % ({
                            'supported_types': supported_types, 'field_type': field.type}))

        Comodel = self.env.get(field.comodel_name)

        model_domain = AND([
            kwargs.get('search_domain', []),
            kwargs.get('category_domain', []),
            kwargs.get('filter_domain', []),
            [(field_name, '!=', False)],
        ])
        comodel_domain = kwargs.get('comodel_domain', [])
        disable_counters = kwargs.get('disable_counters', False)

        group_by = kwargs.get('group_by', False)
        if group_by:
            # determine the labeling of values returned by the group_by field
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

        # get filter_values
        filter_values = []

        if field.type == 'many2one':
            counters = {}
            if not disable_counters:
                groups = self.read_group(model_domain, [field_name], [field_name])
                counters = {
                    group[field_name][0]: group[field_name + '_count']
                    for group in groups
                }
            # retrieve all possible values, and return them with their label and counter
            field_names = ['display_name', group_by] if group_by else ['display_name']
            records = Comodel.search_read(comodel_domain, field_names)
            for record in records:
                record_id = record['id']
                values = {
                    'id': record_id,
                    'name': record['display_name'],
                    'count': counters.get(record_id, 0),
                }
                if group_by:
                    values['group_id'], values['group_name'] = group_id_name(record[group_by])
                filter_values.append(values)

        elif field.type == 'many2many':
            # retrieve all possible values, and return them with their label and counter
            field_names = ['display_name', group_by] if group_by else ['display_name']
            records = Comodel.search_read(comodel_domain, field_names)
            for record in records:
                record_id = record['id']
                values = {
                    'id': record_id,
                    'name': record['display_name'],
                    'count': 0,
                }
                if not disable_counters:
                    count_domain = AND([model_domain, [(field_name, 'in', record_id)]])
                    values['count'] = self.search_count(count_domain)
                if group_by:
                    values['group_id'], values['group_name'] = group_id_name(record[group_by])
                filter_values.append(values)

        elif field.type == 'selection':
            counters = {}
            if not disable_counters:
                groups = self.read_group(model_domain, [field_name], [field_name])
                counters = {
                    group[field_name]: group[field_name + '_count']
                    for group in groups
                }
            # retrieve all possible values, and return them with their label and counter
            selection = self.fields_get([field_name])[field_name]
            for value, label in selection:
                filter_values.append({
                    'id': value,
                    'name': label,
                    'count': counters.get(value, 0),
                })

        return filter_values
