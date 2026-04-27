# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

import babel.dates

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.osv import expression
from odoo.tools.misc import get_lang

DISPLAY_FORMATS = {
    'day': '%d %b %Y',
    'week': 'W%W %Y',
    'month': '%B %Y',
    'year': '%Y',
}


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_cohort_data(self, date_start, date_stop, measure, interval, domain, mode, timeline):
        """
            Get all the data needed to display a cohort view

            :param date_start: the starting date to use in the group_by clause
            :param date_stop: the date field which mark the change of state
            :param measure: the field to aggregate
            :param interval: the interval of time between two cells ('day', 'week', 'month', 'year')
            :param domain: a domain to limit the read_group
            :param mode: the mode of aggregation ('retention', 'churn') [default='retention']
            :param timeline: the direction to display data ('forward', 'backward') [default='forward']
            :return: dictionary containing a total amount of records considered and a
                     list of rows each of which contains 16 cells.
        """
        rows = []
        columns_avg = defaultdict(lambda: dict(percentage=0, count=0))
        total_value = 0
        initial_churn_value = 0
        if measure != '__count':
            domain = expression.AND([domain, [(measure, '!=', False)]])
            measures = [f'{measure}:sum']
            field = self._fields[measure]
            if field.type == 'many2one':
                measure = f'{measure}:count_distinct'
            else:
                measure = f'{measure}:{field.aggregator}'
            measures.append(measure)
        else:
            measures = ['__count', '__count']

        locale = get_lang(self.env).code

        domain = expression.AND([domain, [(date_start, '!=', False)]])  # date not set are no take in account
        row_groups = self._read_group(
            domain=domain,
            groupby=[date_start + ':' + interval],
            aggregates=measures,
        )

        date_start_field = self._fields[date_start]
        if date_start_field.type == 'datetime':
            today = datetime.today()
            convert_method = fields.Datetime.to_datetime
        else:
            today = date.today()
            convert_method = fields.Date.to_date

        for group_value, sum_value, value in row_groups:
            total_value += value
            group_domain = expression.AND([
                domain,
                ['&', (date_start, '>=', group_value), (date_start, '<', group_value + models.READ_GROUP_TIME_GRANULARITY[interval])]
            ])
            sub_group = self._read_group(
                domain=group_domain,
                groupby=[date_stop + ':' + interval],
                aggregates=[measure],
            )
            sub_group_per_period = {
                convert_method(group_value): aggregate_value
                for group_value, aggregate_value in sub_group
            }

            columns = []
            initial_value = sum_value
            col_range = range(-15, 1) if timeline == 'backward' else range(0, 16)
            for col_index, col in enumerate(col_range):
                col_start_date = group_value
                if interval == 'day':
                    col_start_date += relativedelta(days=col)
                    col_end_date = col_start_date + relativedelta(days=1)
                elif interval == 'week':
                    col_start_date += relativedelta(days=7 * col)
                    col_end_date = col_start_date + relativedelta(days=7)
                elif interval == 'month':
                    col_start_date += relativedelta(months=col)
                    col_end_date = col_start_date + relativedelta(months=1)
                else:
                    col_start_date += relativedelta(years=col)
                    col_end_date = col_start_date + relativedelta(years=1)

                if col_start_date > today:
                    columns_avg[col_index]
                    columns.append({
                        'value': '-',
                        'churn_value': '-',
                        'percentage': '',
                    })
                    continue

                col_value = sub_group_per_period.get(col_start_date, 0.0)

                # In backward timeline, if columns are out of given range, we need
                # to set initial value for calculating correct percentage
                if timeline == 'backward' and col_index == 0:
                    outside_timeline_domain = expression.AND(
                        [
                            group_domain,
                            ['|',
                                (date_stop, '=', False),
                                (date_stop, '>=', fields.Datetime.to_string(col_start_date)),
                            ]
                        ]
                    )
                    col_group = self._read_group(
                        domain=outside_timeline_domain,
                        aggregates=[measure],
                    )
                    initial_value = float(col_group[0][0])
                    initial_churn_value = sum_value - initial_value

                previous_col_remaining_value = initial_value if col_index == 0 else columns[-1]['value']
                col_remaining_value = previous_col_remaining_value - col_value
                percentage = sum_value and (col_remaining_value) / sum_value or 0
                if mode == 'churn':
                    percentage = 1 - percentage

                percentage = round(100 * percentage, 1)

                columns_avg[col_index]['percentage'] += percentage
                columns_avg[col_index]['count'] += 1
                # For 'week' interval, we display a better tooltip (range like : '02 Jul - 08 Jul')
                if interval == 'week':
                    period = "%s - %s" % (col_start_date.strftime('%d %b'), (col_end_date - relativedelta(days=1)).strftime('%d %b'))
                else:
                    period = col_start_date.strftime(DISPLAY_FORMATS[interval])

                if mode == 'churn':
                    mode_domain = [
                        (date_stop, '<', col_end_date.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                    ]
                else:
                    mode_domain = ['|',
                        (date_stop, '>=', col_end_date.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                        (date_stop, '=', False),
                    ]

                columns.append({
                    'value': col_remaining_value,
                    'churn_value': col_value + (columns[-1]['churn_value'] if col_index > 0 else initial_churn_value),
                    'percentage': percentage,
                    'domain': mode_domain,
                    'period': period,
                })

            rows.append({
                'date': babel.dates.format_date(
                    group_value, format=models.READ_GROUP_DISPLAY_FORMAT[interval],
                    locale=locale,
                ),
                'value': value,
                'domain': group_domain,
                'columns': columns,
            })

        return {
            'rows': rows,
            'avg': {'avg_value': total_value / len(rows) if rows else 0, 'columns_avg': columns_avg},
        }
