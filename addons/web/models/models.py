# -*- coding: utf-8 -*-
from datetime import datetime
import babel.dates
import pytz

from odoo.tools import pycompat
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo import _, api, fields, models


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

        fields = [progress_bar['field'], group_by]
        records_values = self.search_read(domain or [], fields)

        data = {}
        for record_values in records_values:
            group_by_value = record_values[group_by]

            # Again, imitating what _read_group_format_result and _read_group_prepare_data do
            field_type = self._fields[group_by].type
            if field_type in ['date', 'datetime'] and isinstance(group_by_value, pycompat.string_types):
                locale = self._context.get('lang') or 'en_US'
                dt_format = DEFAULT_SERVER_DATETIME_FORMAT if field_type == 'datetime' else DEFAULT_SERVER_DATE_FORMAT
                group_by_value = datetime.strptime(group_by_value, dt_format)
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
