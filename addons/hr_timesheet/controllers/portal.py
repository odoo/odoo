# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from datetime import datetime

from odoo import fields, http, _
from odoo.http import request
from odoo.tools import date_utils, groupby as groupbyelem
from odoo.osv.expression import AND, OR

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class TimesheetCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'timesheet_count' in counters:
            Timesheet = request.env['account.analytic.line']
            domain = Timesheet._timesheet_get_portal_domain()
            values['timesheet_count'] = Timesheet.sudo().search_count(domain)
        return values

    def _get_searchbar_inputs(self):
        return {
            'all': {'input': 'all', 'label': _('Search in All')},
            'employee': {'input': 'employee', 'label': _('Search in Employee')},
            'project': {'input': 'project', 'label': _('Search in Project')},
            'task': {'input': 'task', 'label': _('Search in Task')},
            'name': {'input': 'name', 'label': _('Search in Description')},
        }

    def _task_get_searchbar_sortings(self):
        values = super()._task_get_searchbar_sortings()
        values['progress'] = {'label': _('Progress'), 'order': 'progress asc', 'sequence': 9}
        return values

    def _get_searchbar_groupby(self):
        return {
            'none': {'input': 'none', 'label': _('None')},
            'project': {'input': 'project', 'label': _('Project')},
            'task': {'input': 'task', 'label': _('Task')},
            'date': {'input': 'date', 'label': _('Date')},
            'employee': {'input': 'employee', 'label': _('Employee')}
        }

    def _get_search_domain(self, search_in, search):
        search_domain = []
        if search_in in ('project', 'all'):
            search_domain = OR([search_domain, [('project_id', 'ilike', search)]])
        if search_in in ('name', 'all'):
            search_domain = OR([search_domain, [('name', 'ilike', search)]])
        if search_in in ('employee', 'all'):
            search_domain = OR([search_domain, [('employee_id', 'ilike', search)]])
        if search_in in ('task', 'all'):
            search_domain = OR([search_domain, [('task_id', 'ilike', search)]])
        return search_domain

    def _get_groupby_mapping(self):
        return {
            'project': 'project_id',
            'task': 'task_id',
            'employee': 'employee_id',
            'date': 'date'
        }

    def _get_searchbar_sortings(self):
        return {
            'date': {'label': _('Newest'), 'order': 'date desc'},
            'employee': {'label': _('Employee'), 'order': 'employee_id'},
            'project': {'label': _('Project'), 'order': 'project_id'},
            'task': {'label': _('Task'), 'order': 'task_id'},
            'name': {'label': _('Description'), 'order': 'name'},
        }

    @http.route(['/my/timesheets', '/my/timesheets/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_timesheets(self, page=1, sortby=None, filterby=None, search=None, search_in='all', groupby='none', **kw):
        Timesheet = request.env['account.analytic.line']
        domain = Timesheet._timesheet_get_portal_domain()
        Timesheet_sudo = Timesheet.sudo()

        values = self._prepare_portal_layout_values()
        _items_per_page = 100

        searchbar_sortings = self._get_searchbar_sortings()

        searchbar_inputs = self._get_searchbar_inputs()

        searchbar_groupby = self._get_searchbar_groupby()

        today = fields.Date.today()
        quarter_start, quarter_end = date_utils.get_quarter(today)
        last_week = today + relativedelta(weeks=-1)
        last_month = today + relativedelta(months=-1)
        last_year = today + relativedelta(years=-1)

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'today': {'label': _('Today'), 'domain': [("date", "=", today)]},
            'week': {'label': _('This week'), 'domain': [('date', '>=', date_utils.start_of(today, "week")), ('date', '<=', date_utils.end_of(today, 'week'))]},
            'month': {'label': _('This month'), 'domain': [('date', '>=', date_utils.start_of(today, 'month')), ('date', '<=', date_utils.end_of(today, 'month'))]},
            'year': {'label': _('This year'), 'domain': [('date', '>=', date_utils.start_of(today, 'year')), ('date', '<=', date_utils.end_of(today, 'year'))]},
            'quarter': {'label': _('This Quarter'), 'domain': [('date', '>=', quarter_start), ('date', '<=', quarter_end)]},
            'last_week': {'label': _('Last week'), 'domain': [('date', '>=', date_utils.start_of(last_week, "week")), ('date', '<=', date_utils.end_of(last_week, 'week'))]},
            'last_month': {'label': _('Last month'), 'domain': [('date', '>=', date_utils.start_of(last_month, 'month')), ('date', '<=', date_utils.end_of(last_month, 'month'))]},
            'last_year': {'label': _('Last year'), 'domain': [('date', '>=', date_utils.start_of(last_year, 'year')), ('date', '<=', date_utils.end_of(last_year, 'year'))]},
        }
        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain = AND([domain, searchbar_filters[filterby]['domain']])

        if search and search_in:
            domain += self._get_search_domain(search_in, search)

        timesheet_count = Timesheet_sudo.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/timesheets",
            url_args={'sortby': sortby, 'search_in': search_in, 'search': search, 'filterby': filterby, 'groupby': groupby},
            total=timesheet_count,
            page=page,
            step=_items_per_page
        )

        def get_timesheets():
            groupby_mapping = self._get_groupby_mapping()
            field = groupby_mapping.get(groupby, None)
            orderby = '%s, %s' % (field, order) if field else order
            timesheets = Timesheet_sudo.search(domain, order=orderby, limit=_items_per_page, offset=pager['offset'])
            if field:
                if groupby == 'date':
                    time_data = Timesheet_sudo.read_group(domain, ['date', 'unit_amount:sum'], ['date:day'])
                    mapped_time = dict([(datetime.strptime(m['date:day'], '%d %b %Y').date(), m['unit_amount']) for m in time_data])
                    grouped_timesheets = [(Timesheet_sudo.concat(*g), mapped_time[k]) for k, g in groupbyelem(timesheets, itemgetter('date'))]
                else:
                    time_data = time_data = Timesheet_sudo.read_group(domain, [field, 'unit_amount:sum'], [field])
                    mapped_time = dict([(m[field][0] if m[field] else False, m['unit_amount']) for m in time_data])
                    grouped_timesheets = [(Timesheet_sudo.concat(*g), mapped_time[k.id]) for k, g in groupbyelem(timesheets, itemgetter(field))]
                return timesheets, grouped_timesheets

            grouped_timesheets = [(
                timesheets,
                sum(Timesheet_sudo.search(domain).mapped('unit_amount'))
            )] if timesheets else []
            return timesheets, grouped_timesheets

        timesheets, grouped_timesheets = get_timesheets()

        values.update({
            'timesheets': timesheets,
            'grouped_timesheets': grouped_timesheets,
            'page_name': 'timesheet',
            'default_url': '/my/timesheets',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'search_in': search_in,
            'search': search,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'is_uom_day': request.env['account.analytic.line']._is_timesheet_encode_uom_day(),
        })
        return request.render("hr_timesheet.portal_my_timesheets", values)
