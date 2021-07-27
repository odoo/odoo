# -*- coding: utf-8 -*-
import babel.dates
import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import date_utils


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
        group_by_fname = group_by.partition(':')[0]
        field_type = self._fields[group_by_fname].type
        if field_type == 'selection':
            selection_labels = dict(self.fields_get()[group_by]['selection'])

        def adapt(value):
            if field_type == 'selection':
                value = selection_labels.get(value, False)
            if type(value) == tuple:
                value = value[1]  # FIXME should use technical value (0)
            return value

        result = {}
        for group in self._read_progress_bar(domain, group_by, progress_bar):
            group_by_value = str(adapt(group[group_by]))
            field_value = group[progress_bar['field']]
            if group_by_value not in result:
                result[group_by_value] = dict.fromkeys(progress_bar['colors'], 0)
            if field_value in result[group_by_value]:
                result[group_by_value][field_value] += group['__count']
        return result

    def _read_progress_bar(self, domain, group_by, progress_bar):
        """ Implementation of read_progress_bar() that returns results in the
            format of read_group().
        """
        try:
            fname = progress_bar['field']
            return self.read_group(domain, [fname], [group_by, fname], lazy=False)
        except UserError:
            # possibly failed because of grouping on or aggregating non-stored
            # field; fallback on alternative implementation
            pass

        # Workaround to match read_group's infrastructure
        # TO DO in master: harmonize this function and readgroup to allow factorization
        group_by_name = group_by.partition(':')[0]
        group_by_modifier = group_by.partition(':')[2] or 'month'

        records_values = self.search_read(domain or [], [progress_bar['field'], group_by_name])
        field_type = self._fields[group_by_name].type

        for record_values in records_values:
            group_by_value = record_values.pop(group_by_name)

            # Again, imitating what _read_group_format_result and _read_group_prepare_data do
            if group_by_value and field_type in ['date', 'datetime']:
                locale = self._context.get('lang') or 'en_US'
                group_by_value = date_utils.start_of(fields.Datetime.to_datetime(group_by_value), group_by_modifier)
                group_by_value = pytz.timezone('UTC').localize(group_by_value)
                tz_info = None
                if field_type == 'datetime' and self._context.get('tz') in pytz.all_timezones:
                    tz_info = self._context.get('tz')
                    group_by_value = babel.dates.format_datetime(
                        group_by_value, format=DISPLAY_DATE_FORMATS[group_by_modifier],
                        tzinfo=tz_info, locale=locale)
                else:
                    group_by_value = babel.dates.format_date(
                        group_by_value, format=DISPLAY_DATE_FORMATS[group_by_modifier],
                        locale=locale)

            record_values[group_by] = group_by_value
            record_values['__count'] = 1

        return records_values
