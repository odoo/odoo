# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from operator import itemgetter

from odoo import fields, http, _
from odoo.http import request
from odoo.tools import date_utils, groupby as groupbyelem
from odoo.osv.expression import AND, FALSE_DOMAIN

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.addons.project.controllers.portal import ProjectCustomerPortal


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
            'name': {'input': 'name', 'label': _('Search in Description'), 'sequence': 10},
            'employee_id': {'input': 'employee_id', 'label': _('Search in Employee'), 'sequence': 20},
            'project_id': {'input': 'project_id', 'label': _('Search in Project'), 'sequence': 30},
            'task_id': {'input': 'task_id', 'label': _('Search in Task'), 'sequence': 40},
            'parent_task_id': {'input': 'parent_task_id', 'label': _('Search in Parent Task'), 'sequence': 70},
        }

    def _task_get_searchbar_sortings(self, milestones_allowed, project=False):
        return super()._task_get_searchbar_sortings(milestones_allowed, project) | {
            'progress asc': {'label': _('Progress'), 'order': 'progress asc', 'sequence': 100},
        }

    def _get_searchbar_groupby(self):
        return {
            'none': {'label': _('None'), 'sequence': 10},
            'date': {'label': _('Date'), 'sequence': 20},
            'project_id': {'label': _('Project'), 'sequence': 30},
            'parent_task_id': {'label': _('Parent Task'), 'sequence': 40},
            'task_id': {'label': _('Task'), 'sequence': 50},
            'employee_id': {'label': _('Employee'), 'sequence': 70},
        }

    def _get_search_domain(self, search_in, search):
        if search_in in self._get_searchbar_inputs():
            return [(search_in, 'ilike', search)]
        else:
            return FALSE_DOMAIN

    def _get_searchbar_sortings(self):
        return {
            'date desc': {'label': _('Newest')},
            'employee_id': {'label': _('Employee')},
            'project_id': {'label': _('Project')},
            'task_id': {'label': _('Task')},
            'name': {'label': _('Description')},
        }

    def _project_get_page_view_values(self, project, access_token, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='content', groupby=None, **kwargs):
        values = super()._project_get_page_view_values(project, access_token, page, date_begin, date_end, sortby, search, search_in, groupby, **kwargs)
        values['allow_timesheets'] = project.allow_timesheets
        return values

    @http.route(['/my/timesheets', '/my/timesheets/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_timesheets(self, page=1, sortby=None, filterby=None, search=None, search_in='all', groupby='none', **kw):
        if not self._check_page_visibility("hr_timesheet.portal_my_home_timesheet"):
            return request.not_found()
        Timesheet = request.env['account.analytic.line']
        domain = Timesheet._timesheet_get_portal_domain()
        Timesheet_sudo = Timesheet.sudo()

        values = self._prepare_portal_layout_values()
        _items_per_page = 100

        searchbar_sortings = self._get_searchbar_sortings()

        searchbar_inputs = dict(sorted(self._get_searchbar_inputs().items(), key=lambda item: item[1]['sequence']))

        searchbar_groupby = dict(sorted(self._get_searchbar_groupby().items(), key=lambda item: item[1]['sequence']))

        today = fields.Date.today()
        quarter_start, quarter_end = date_utils.get_quarter(today)
        last_quarter_date = date_utils.subtract(quarter_start, weeks=1)
        last_quarter_start, last_quarter_end = date_utils.get_quarter(last_quarter_date)
        last_week = today + relativedelta(weeks=-1)
        last_month = today + relativedelta(months=-1)
        last_year = today + relativedelta(years=-1)

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'last_year': {'label': _('Last Year'), 'domain': [('date', '>=', date_utils.start_of(last_year, 'year')), ('date', '<=', date_utils.end_of(last_year, 'year'))]},
            'last_quarter': {'label': _('Last Quarter'), 'domain': [('date', '>=', last_quarter_start), ('date', '<=', last_quarter_end)]},
            'last_month': {'label': _('Last Month'), 'domain': [('date', '>=', date_utils.start_of(last_month, 'month')), ('date', '<=', date_utils.end_of(last_month, 'month'))]},
            'last_week': {'label': _('Last Week'), 'domain': [('date', '>=', date_utils.start_of(last_week, "week")), ('date', '<=', date_utils.end_of(last_week, 'week'))]},
            'today': {'label': _('Today'), 'domain': [("date", "=", today)]},
            'week': {'label': _('This Week'), 'domain': [('date', '>=', date_utils.start_of(today, "week")), ('date', '<=', date_utils.end_of(today, 'week'))]},
            'month': {'label': _('This Month'), 'domain': [('date', '>=', date_utils.start_of(today, 'month')), ('date', '<=', date_utils.end_of(today, 'month'))]},
            'quarter': {'label': _('This Quarter'), 'domain': [('date', '>=', quarter_start), ('date', '<=', quarter_end)]},
            'year': {'label': _('This Year'), 'domain': [('date', '>=', date_utils.start_of(today, 'year')), ('date', '<=', date_utils.end_of(today, 'year'))]},
        }
        # default sort by value
        if not sortby:
            sortby = 'date desc'
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain = AND([domain, searchbar_filters[filterby]['domain']])

        if search and search_in:
            domain = AND([domain, self._get_search_domain(search_in, search)])

        if parent_task_id := kw.get('parent_task_id'):
            domain = AND([domain, [('parent_task_id', '=', int(parent_task_id))]])

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
            field = None if groupby == 'none' else groupby
            orderby = '%s, %s' % (field, sortby) if field else sortby
            timesheets = Timesheet_sudo.search(domain, order=orderby, limit=_items_per_page, offset=pager['offset'])
            if field:
                if groupby == 'date':
                    raw_timesheets_group = Timesheet_sudo._read_group(
                        domain, ['date:day'], ['unit_amount:sum', 'id:recordset'], order='date:day desc'
                    )
                    grouped_timesheets = [(records, unit_amount) for __, unit_amount, records in raw_timesheets_group]

                else:
                    time_data = Timesheet_sudo._read_group(domain, [field], ['unit_amount:sum'])
                    mapped_time = {field.id: unit_amount for field, unit_amount in time_data}
                    grouped_timesheets = [(Timesheet_sudo.concat(*g), mapped_time[k.id]) for k, g in groupbyelem(timesheets, itemgetter(field))]
                return timesheets, grouped_timesheets

            grouped_timesheets = [(
                timesheets,
                Timesheet_sudo._read_group(domain, aggregates=['unit_amount:sum'])[0][0]
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
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'is_uom_day': request.env['account.analytic.line']._is_timesheet_encode_uom_day(),
        })
        return request.render("hr_timesheet.portal_my_timesheets", values)

class TimesheetProjectCustomerPortal(ProjectCustomerPortal):

    def _show_task_report(self, task_sudo, report_type, download):
        domain = request.env['account.analytic.line']._timesheet_get_portal_domain()
        task_domain = AND([domain, [('task_id', '=', task_sudo.id)]])
        timesheets = request.env['account.analytic.line'].sudo().search(task_domain)
        return self._show_report(model=timesheets,
            report_type=report_type, report_ref='hr_timesheet.timesheet_report_task_timesheets', download=download)

    def _prepare_tasks_values(self, page, date_begin, date_end, sortby, search, search_in, groupby, url="/my/tasks", domain=None, su=False, project=False):
        values = super()._prepare_tasks_values(page, date_begin, date_end, sortby, search, search_in, groupby, url, domain, su, project)
        values.update(
            is_uom_day=request.env['account.analytic.line']._is_timesheet_encode_uom_day(),
        )

        return values
