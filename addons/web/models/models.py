# -*- coding: utf-8 -*-
import babel.dates
import pytz

from odoo import _, api, fields, models
from odoo.tools import lazy

class IrActionsActWindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=[('qweb', 'QWeb')])

class Base(models.AbstractModel):
    _inherit = 'base'

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
