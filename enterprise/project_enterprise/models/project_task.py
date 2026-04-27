# Part of Odoo. See LICENSE file for full copyright and licensing details.

import heapq
from pytz import utc, timezone
from collections import defaultdict
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from odoo.tools.date_utils import get_timedelta

from odoo import api, fields, models
from odoo.osv import expression
from odoo.exceptions import UserError
from odoo.tools import _, format_list, topological_sort
from odoo.tools.sql import SQL
from odoo.addons.resource.models.utils import filter_domain_leaf
from odoo.osv.expression import is_leaf

from odoo.addons.resource.models.utils import Intervals, sum_intervals

PROJECT_TASK_WRITABLE_FIELDS = {
    'planned_date_begin',
}


class Task(models.Model):
    _inherit = "project.task"

    planned_date_begin = fields.Datetime("Start date", tracking=True)
    # planned_date_start is added to be able to display tasks in calendar view because both start and end date are mandatory
    planned_date_start = fields.Datetime(compute="_compute_planned_date_start", inverse='_inverse_planned_date_start', search="_search_planned_date_start")
    allocated_hours = fields.Float(compute='_compute_allocated_hours', store=True, readonly=False)
    # Task Dependencies fields
    display_warning_dependency_in_gantt = fields.Boolean(compute="_compute_display_warning_dependency_in_gantt", export_string_translation=False)
    planning_overlap = fields.Html(compute='_compute_planning_overlap', search='_search_planning_overlap', export_string_translation=False)
    dependency_warning = fields.Html(compute='_compute_dependency_warning', search='_search_dependency_warning', export_string_translation=False)

    # User names in popovers
    user_names = fields.Char(compute='_compute_user_names', export_string_translation=False)
    user_ids = fields.Many2many(group_expand="_group_expand_user_ids")
    partner_id = fields.Many2one(group_expand="_group_expand_partner_ids")
    project_id = fields.Many2one(group_expand="_group_expand_project_ids")

    _sql_constraints = [
        ('planned_dates_check', "CHECK ((planned_date_begin <= date_deadline))", "The planned start date must be before the planned end date."),
    ]

    # action_gantt_reschedule utils
    _WEB_GANTT_RESCHEDULE_WORK_INTERVALS_CACHE_KEY = 'work_intervals'
    _WEB_GANTT_RESCHEDULE_RESOURCE_VALIDITY_CACHE_KEY = 'resource_validity'

    @property
    def SELF_WRITABLE_FIELDS(self):
        return super().SELF_WRITABLE_FIELDS | PROJECT_TASK_WRITABLE_FIELDS

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if self.env.context.get('scale', False) not in ("month", "year"):
            return result

        planned_date_begin = result.get('planned_date_begin', self.env.context.get('planned_date_begin', False))
        date_deadline = result.get('date_deadline', self.env.context.get('date_deadline', False))
        if planned_date_begin and date_deadline:
            user_ids = self.env.context.get('user_ids', [])
            planned_date_begin, date_deadline = self._calculate_planned_dates(planned_date_begin, date_deadline, user_ids)
            result.update(planned_date_begin=planned_date_begin, date_deadline=date_deadline)
        return result

    def action_unschedule_task(self):
        self.write({
            'planned_date_begin': False,
            'date_deadline': False
        })

    @api.depends('is_closed')
    def _compute_display_warning_dependency_in_gantt(self):
        for task in self:
            task.display_warning_dependency_in_gantt = not task.is_closed

    @api.onchange('date_deadline', 'planned_date_begin')
    def _onchange_planned_dates(self):
        if not self.date_deadline:
            self.planned_date_begin = False

    @api.depends('date_deadline', 'planned_date_begin', 'user_ids')
    def _compute_allocated_hours(self):
        for task in self:
            if not task.date_deadline or not task.planned_date_begin:
                task.allocated_hours = 0
                continue
            date_begin, date_end = task._calculate_planned_dates(
                task.planned_date_begin,
                task.date_deadline,
                user_id=task.user_ids.ids if len(task.user_ids) == 1 else None,
                calendar=task.env.company.resource_calendar_id if len(task.user_ids) != 1 else None,
            )
            if len(task.user_ids) == 1:
                tz = task.user_ids.tz or 'UTC'
                # We need to browse on res.users in order to bypass the new origin id
                work_intervals, _dummy = task.user_ids.sudo()._get_valid_work_intervals(
                    date_begin.astimezone(timezone(tz)),
                    date_end.astimezone(timezone(tz))
                )
                work_duration = sum_intervals(work_intervals[task.user_ids._ids[0]])
            else:
                tz = task.env.company.resource_calendar_id.tz or 'UTC'
                work_duration = task.env.company.resource_calendar_id.get_work_hours_count(
                    date_begin.astimezone(timezone(tz)),
                    date_end.astimezone(timezone(tz)),
                    compute_leaves=False
                )
            task.allocated_hours = round(work_duration, 2)

    def _fetch_planning_overlap(self, additional_domain=None):
        domain = [
            ('active', '=', True),
            ('is_closed', '=', False),
            ('planned_date_begin', '!=', False),
            ('date_deadline', '!=', False),
            ('date_deadline', '>', fields.Datetime.now()),
            ('project_id', '!=', False),
        ]
        if additional_domain:
            domain = expression.AND([domain, additional_domain])
        Task = self.env['project.task']
        planning_overlap_query = Task._where_calc(
            expression.AND([
                domain,
                [('id', 'in', self.ids)]
            ])
        )
        tu1_alias = planning_overlap_query.join(Task._table, 'id', 'project_task_user_rel', 'task_id', 'TU1')
        task2_alias = planning_overlap_query.make_alias(Task._table, 'T2')
        task2_expression = expression.expression(domain, Task, task2_alias)
        task2_query = task2_expression.query

        # add additional condition to join with the main query
        task2_query.add_where(
            SQL(
                "%s != %s",
                SQL.identifier(task2_alias, 'id'),
                SQL.identifier(self._table, 'id')
            )
        )
        task2_query.add_where(
            SQL(
                "(%s::TIMESTAMP, %s::TIMESTAMP) OVERLAPS (%s::TIMESTAMP, %s::TIMESTAMP)",
                SQL.identifier(Task._table, 'planned_date_begin'),
                SQL.identifier(Task._table, 'date_deadline'),
                SQL.identifier(task2_alias, 'planned_date_begin'),
                SQL.identifier(task2_alias, 'date_deadline')
            )
        )

        # join task2 query with the main query
        planning_overlap_query.add_join(
            'JOIN',
            task2_alias,
            Task._table,
            task2_query.where_clause
        )
        tu2_alias = planning_overlap_query.join(task2_alias, 'id', 'project_task_user_rel', 'task_id', 'TU2')
        planning_overlap_query.add_where(
            SQL(
                "%s = %s",
                SQL.identifier(tu1_alias, 'user_id'),
                SQL.identifier(tu2_alias, 'user_id')
            )
        )
        user_alias = planning_overlap_query.join(tu1_alias, 'user_id', 'res_users', 'id', 'U')
        partner_alias = planning_overlap_query.join(user_alias, 'partner_id', 'res_partner', 'id', 'P')
        query_str = planning_overlap_query.select(
            SQL.identifier(Task._table, 'id'),
            SQL.identifier(Task._table, 'planned_date_begin'),
            SQL.identifier(Task._table, 'date_deadline'),
            SQL("ARRAY_AGG(%s) AS task_ids", SQL.identifier(task2_alias, 'id')),
            SQL("MIN(%s)", SQL.identifier(task2_alias, 'planned_date_begin')),
            SQL("MAX(%s)", SQL.identifier(task2_alias, 'date_deadline')),
            SQL("%s AS user_id", SQL.identifier(user_alias, 'id')),
            SQL("%s AS partner_name", SQL.identifier(partner_alias, 'name')),
            SQL("%s", SQL.identifier(Task._table, 'allocated_hours')),
            SQL("SUM(%s)", SQL.identifier(task2_alias, 'allocated_hours')),
        )

        self.env.cr.execute(
            SQL(
                """
                    %s
                    GROUP BY %s
                    ORDER BY %s
                """,
                query_str,
                SQL(", ").join([
                    SQL.identifier(Task._table, 'id'),
                    SQL.identifier(user_alias, 'id'),
                    SQL.identifier(partner_alias, 'name'),
                ]),
                SQL.identifier(partner_alias, 'name'),
            )
        )
        return self.env.cr.dictfetchall()

    def _get_planning_overlap_per_task(self):
        if not self.ids:
            return {}
        self.flush_model(['active', 'planned_date_begin', 'date_deadline', 'user_ids', 'project_id', 'is_closed'])

        res = defaultdict(lambda: defaultdict(lambda: {
            'overlapping_tasks_ids': [],
            'sum_allocated_hours': 0,
            'min_planned_date_begin': False,
            'max_date_deadline': False,
        }))
        for row in self._fetch_planning_overlap([('allocated_hours', '>', 0)]):
            res[row['id']][row['user_id']] = {
                'partner_name': row['partner_name'],
                'overlapping_tasks_ids': row['task_ids'],
                'sum_allocated_hours': row['sum'] + row['allocated_hours'],
                'min_planned_date_begin': min(row['min'], row['planned_date_begin']),
                'max_date_deadline': max(row['max'], row['date_deadline'])
            }
        return res

    @api.depends('planned_date_begin', 'date_deadline', 'user_ids')
    def _compute_planning_overlap(self):
        overlap_mapping = self._get_planning_overlap_per_task()
        if not overlap_mapping:
            self.planning_overlap = False
            return overlap_mapping
        user_ids = set()
        absolute_min_start = utc.localize(self[0].planned_date_begin or datetime.utcnow())
        absolute_max_end = utc.localize(self[0].date_deadline or datetime.utcnow())
        for task in self:
            for user_id, task_mapping in overlap_mapping.get(task.id, {}).items():
                absolute_min_start = min(absolute_min_start, utc.localize(task_mapping["min_planned_date_begin"]))
                absolute_max_end = max(absolute_max_end, utc.localize(task_mapping["max_date_deadline"]))
                user_ids.add(user_id)
        users = self.env['res.users'].browse(list(user_ids))
        users_work_intervals, dummy = users.sudo()._get_valid_work_intervals(absolute_min_start, absolute_max_end)
        res = {}
        for task in self:
            overlap_messages = []
            for user_id, task_mapping in overlap_mapping.get(task.id, {}).items():
                task_intervals = Intervals([
                    (utc.localize(task_mapping['min_planned_date_begin']),
                     utc.localize(task_mapping['max_date_deadline']),
                     self.env['resource.calendar.attendance'])
                ])
                if task_mapping['sum_allocated_hours'] > sum_intervals((users_work_intervals[user_id] & task_intervals)):
                    overlap_messages.append(_(
                        '%(partner)s has %(amount)s tasks at the same time.',
                        partner=task_mapping["partner_name"],
                        amount=len(task_mapping['overlapping_tasks_ids']),
                    ))
                    if task.id not in res:
                        res[task.id] = {}
                    res[task.id][user_id] = task_mapping
            task.planning_overlap = ' '.join(overlap_messages) or False
        return res

    @api.model
    def _search_planning_overlap(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise NotImplementedError(_('Operation not supported, you should always compare planning_overlap to True or False.'))

        sql = SQL("""(
            SELECT T1.id
            FROM project_task T1
            INNER JOIN project_task T2 ON T1.id <> T2.id
            INNER JOIN project_task_user_rel U1 ON T1.id = U1.task_id
            INNER JOIN project_task_user_rel U2 ON T2.id = U2.task_id
                AND U1.user_id = U2.user_id
            WHERE
                T1.planned_date_begin < T2.date_deadline
                AND T1.date_deadline > T2.planned_date_begin
                AND T1.planned_date_begin IS NOT NULL
                AND T1.date_deadline IS NOT NULL
                AND T1.date_deadline > NOW() AT TIME ZONE 'UTC'
                AND T1.active = 't'
                AND T1.state IN ('01_in_progress', '02_changes_requested', '03_approved', '04_waiting_normal')
                AND T1.project_id IS NOT NULL
                AND T2.planned_date_begin IS NOT NULL
                AND T2.date_deadline IS NOT NULL
                AND T2.date_deadline > NOW() AT TIME ZONE 'UTC'
                AND T2.project_id IS NOT NULL
                AND T2.active = 't'
                AND T2.state IN ('01_in_progress', '02_changes_requested', '03_approved', '04_waiting_normal')
        )""")
        operator_new = "in" if ((operator == "=" and value) or (operator == "!=" and not value)) else "not in"
        return [('id', operator_new, sql)]

    def _compute_user_names(self):
        for task in self:
            task.user_names = format_list(self.env, task.user_ids.mapped('name'))

    @api.model
    def _calculate_planned_dates(self, date_start, date_stop, user_id=None, calendar=None):
        if not (date_start and date_stop):
            raise UserError(_('One parameter is missing to use this method. You should give a start and end dates.'))
        start, stop = date_start, date_stop
        if isinstance(start, str):
            start = fields.Datetime.from_string(start)
        if isinstance(stop, str):
            stop = fields.Datetime.from_string(stop)

        if not calendar:
            user = self.env['res.users'].sudo().browse(user_id) if user_id and user_id != self.env.user.id else self.env.user
            calendar = user.resource_calendar_id or self.env.company.resource_calendar_id
            if not calendar:  # Then we stop and return the dates given in parameter.
                return date_start, date_stop

        if not start.tzinfo:
            start = start.replace(tzinfo=utc)
        if not stop.tzinfo:
            stop = stop.replace(tzinfo=utc)

        intervals = calendar._work_intervals_batch(start, stop)[False]
        if not intervals:  # Then we stop and return the dates given in parameter
            return date_start, date_stop
        list_intervals = [(start, stop) for start, stop, records in intervals]  # Convert intervals in interval list
        start = list_intervals[0][0].astimezone(utc).replace(tzinfo=None)  # We take the first date in the interval list
        stop = list_intervals[-1][1].astimezone(utc).replace(tzinfo=None)  # We take the last date in the interval list
        return start, stop

    def _get_tasks_by_resource_calendar_dict(self):
        """
            Returns a dict of:
                key = 'resource.calendar'
                value = recordset of 'project.task'
        """
        default_calendar = self.env.company.resource_calendar_id

        calendar_by_user_dict = {  # key: user_id, value: resource.calendar instance
            user.id:
                user.resource_calendar_id or default_calendar
            for user in self.mapped('user_ids')
        }

        tasks_by_resource_calendar_dict = defaultdict(
            lambda: self.env[self._name])  # key = resource_calendar instance, value = tasks
        for task in self:
            if len(task.user_ids) == 1:
                tasks_by_resource_calendar_dict[calendar_by_user_dict[task.user_ids.id]] |= task
            else:
                tasks_by_resource_calendar_dict[default_calendar] |= task

        return tasks_by_resource_calendar_dict

    @api.depends('planned_date_begin', 'depend_on_ids.date_deadline')
    def _compute_dependency_warning(self):
        if not self._origin:
            self.dependency_warning = False
            return

        self.flush_model(['planned_date_begin', 'date_deadline'])
        query = """
            SELECT t1.id,
                   ARRAY_AGG(t2.name) as depends_on_names
              FROM project_task t1
              JOIN task_dependencies_rel d
                ON d.task_id = t1.id
              JOIN project_task t2
                ON d.depends_on_id = t2.id
             WHERE t1.id IN %s
               AND t1.planned_date_begin IS NOT NULL
               AND t2.date_deadline IS NOT NULL
               AND t2.date_deadline > t1.planned_date_begin
          GROUP BY t1.id
	    """
        self._cr.execute(query, (tuple(self.ids),))
        depends_on_names_for_id = {
            group['id']: group['depends_on_names']
            for group in self._cr.dictfetchall()
        }
        for task in self:
            depends_on_names = depends_on_names_for_id.get(task.id)
            task.dependency_warning = depends_on_names and _(
                'This task cannot be planned before the following tasks on which it depends: %(task_list)s',
                task_list=format_list(self.env, depends_on_names)
            )

    @api.model
    def _search_dependency_warning(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise NotImplementedError(_('Operation not supported, you should always compare dependency_warning to True or False.'))

        sql = SQL("""
            SELECT t1.id
              FROM project_task t1
              JOIN task_dependencies_rel d
                ON d.task_id = t1.id
              JOIN project_task t2
                ON d.depends_on_id = t2.id
             WHERE t1.planned_date_begin IS NOT NULL
               AND t2.date_deadline IS NOT NULL
               AND t2.date_deadline > t1.planned_date_begin
        """)
        operator_new = "in" if ((operator == "=" and value) or (operator == "!=" and not value)) else "not in"
        return [('id', operator_new, sql)]

    @api.depends('planned_date_begin', 'date_deadline')
    def _compute_planned_date_start(self):
        for task in self:
            task.planned_date_start = task.planned_date_begin or task.date_deadline

    def _inverse_planned_date_start(self):
        """ Inverse method only used for calendar view to update the date start if the date begin was defined """
        for task in self:
            if task.planned_date_begin:
                task.planned_date_begin = task.planned_date_start
            else:  # to keep the right hour in the date_deadline
                task.date_deadline = task.planned_date_start

    def _inverse_state(self):
        super()._inverse_state()
        self.filtered(
            lambda t:
                t.state == '1_canceled'
                and t.planned_date_begin
                and t.planned_date_begin > fields.Datetime.now()
        ).write({
            'planned_date_begin': False,
            'date_deadline': False,
        })

    def _search_planned_date_start(self, operator, value):
        return [
            '|',
            '&', ("planned_date_begin", "!=", False), ("planned_date_begin", operator, value),
            '&', '&', ("planned_date_begin", "=", False), ("date_deadline", "!=", False), ("date_deadline", operator, value),
        ]

    def write(self, vals):
        compute_default_planned_dates = None
        compute_allocated_hours = None
        date_start_update = 'planned_date_begin' in vals and vals['planned_date_begin'] is not False
        date_end_update = 'date_deadline' in vals and vals['date_deadline'] is not False
        # if fsm_mode=True then the processing in industry_fsm module is done for these dates.
        if date_start_update and date_end_update \
           and not any(task.planned_date_begin or task.date_deadline for task in self):
            if len(self) > 1:
                compute_default_planned_dates = self.filtered(lambda task: not task.planned_date_begin)
            if not vals.get('allocated_hours') and vals.get('planned_date_begin') and vals.get('date_deadline'):
                compute_allocated_hours = self.filtered(lambda task: not task.allocated_hours)

        # if date_end was set to False, so we set planned_date_begin to False
        if not vals.get('date_deadline', True):
            vals['planned_date_begin'] = False

        if compute_default_planned_dates:
            # Take the default planned dates
            planned_date_begin = vals.get('planned_date_begin', False)
            date_deadline = vals.get('date_deadline', False)

            # Then sort the tasks by resource_calendar and finally compute the planned dates
            tasks_by_resource_calendar_dict = compute_default_planned_dates.sudo()._get_tasks_by_resource_calendar_dict()

            for (calendar, _dummy) in tasks_by_resource_calendar_dict.items():
                date_start, date_stop = self._calculate_planned_dates(planned_date_begin, date_deadline,
                                                                       calendar=calendar)
                vals['planned_date_begin'] = date_start
                vals['date_deadline'] = date_stop

        res = super().write(vals)

        # Get the tasks which are either not linked to a project or their project has not timesheet tracking
        tasks_without_timesheets_track = self.filtered(lambda task: (
            'allocated_hours' not in vals and
            (task.planned_date_begin and task.date_deadline) and
            ("allow_timesheet" in task.project_id and not task.project_id.allow_timesheet)
        ))
        if tasks_without_timesheets_track:
            tasks_without_timesheets_track._set_allocated_hours_for_tasks()

        if compute_allocated_hours:
            # 1) Calculate capacity for selected period
            start = fields.Datetime.from_string(vals['planned_date_begin'])
            stop = fields.Datetime.from_string(vals['date_deadline'])
            if not start.tzinfo:
                start = start.replace(tzinfo=utc)
            if not stop.tzinfo:
                stop = stop.replace(tzinfo=utc)

            resource = compute_allocated_hours.sudo().user_ids._get_project_task_resource()
            if len(resource) == 1 and resource.calendar_id:
                # First case : trying to plan tasks for a single user that has its own calendar => using user's calendar
                calendar = resource.calendar_id
                work_intervals = calendar._work_intervals_batch(start, stop, resources=resource)
                capacity = sum_intervals(work_intervals[resource.id])
            else:
                # Second case : trying to plan tasks for a single user that has no calendar / for multiple users => using company's calendar
                calendar = self.env.company.resource_calendar_id
                work_intervals = calendar._work_intervals_batch(start, stop)
                capacity = sum_intervals(work_intervals[False])

            # 2) Plan tasks without assignees
            tasks_no_assignees = compute_allocated_hours.filtered(lambda task: not task.user_ids)
            if tasks_no_assignees:
                if calendar == self.env.company.resource_calendar_id:
                    hours = capacity # we can avoid recalculating the amount here
                else:
                    calendar = self.env.company.resource_calendar_id
                    hours = sum_intervals(calendar._work_intervals_batch(start, stop)[False])
                tasks_no_assignees.write({"allocated_hours": hours})
            compute_allocated_hours -= tasks_no_assignees

            if compute_allocated_hours: # this recordset could be empty, and we don't want to divide by 0 when checking the length of it
                # 3) Remove the already set allocated hours from the capacity
                capacity -= sum((self - compute_allocated_hours).filtered(lambda task: task.allocated_hours and task.user_ids).mapped('allocated_hours'))

                # 4) Split capacity for every task and plan them
                if capacity > 0:
                    compute_allocated_hours.sudo().write({"allocated_hours": capacity / len(compute_allocated_hours)})

        return res

    def _set_allocated_hours_for_tasks(self):
        tasks_by_resource_calendar_dict = self._get_tasks_by_resource_calendar_dict()
        for (calendar, tasks) in tasks_by_resource_calendar_dict.items():
            # 1. Get the min start and max end among the tasks
            absolute_min_start, absolute_max_end = tasks[0].planned_date_begin, tasks[0].date_deadline
            for task in tasks:
                absolute_max_end = max(absolute_max_end, task.date_deadline)
                absolute_min_start = min(absolute_min_start, task.planned_date_begin)
            start = fields.Datetime.from_string(absolute_min_start)
            stop = fields.Datetime.from_string(absolute_max_end)
            if not start.tzinfo:
                start = start.replace(tzinfo=utc)
            if not stop.tzinfo:
                stop = stop.replace(tzinfo=utc)
            # 2. Fetch the working hours between min start and max end
            work_intervals = calendar._work_intervals_batch(start, stop)[False]
            # 3. For each task compute and write the allocated hours corresponding to their planned dates
            for task in tasks:
                start = task.planned_date_begin
                stop = task.date_deadline
                if not start.tzinfo:
                    start = start.replace(tzinfo=utc)
                if not stop.tzinfo:
                    stop = stop.replace(tzinfo=utc)
                allocated_hours = sum_intervals(work_intervals & Intervals([(start, stop, self.env['resource.calendar.attendance'])]))
                task.allocated_hours = allocated_hours

    def _get_additional_users(self, domain):
        return self.env['res.users']

    def _group_expand_user_ids(self, users, domain):
        """ Group expand by user_ids in gantt view :
            all users which have and open task in this project + the current user if not filtered by assignee
        """
        additional_users = self._get_additional_users(domain)
        if additional_users:
            return additional_users
        start_date = self._context.get('gantt_start_date')
        scale = self._context.get('gantt_scale')
        if not (start_date and scale):
            return additional_users
        domain = filter_domain_leaf(domain, lambda field: field not in ['planned_date_begin', 'date_deadline', 'state'])
        search_on_comodel = self._search_on_comodel(domain, "user_ids", "res.users")
        if search_on_comodel:
            return search_on_comodel
        start_date = fields.Datetime.from_string(start_date)
        delta = get_timedelta(1, scale)
        domain_expand = expression.AND([
            self._group_expand_user_ids_domain([
                ('planned_date_begin', '>=', start_date - delta),
                ('date_deadline', '<', start_date + delta)
            ]),
            domain,
        ])
        return self.search(domain_expand).user_ids.filtered(lambda user: user.active) | self.env.user

    def _group_expand_user_ids_domain(self, domain_expand):
        project_id = self._context.get('default_project_id')
        if project_id:
            domain_expand = expression.OR([[
                ('project_id', '=', project_id),
                ('is_closed', '=', False),
                ('planned_date_begin', '=', False),
                ('date_deadline', '=', False),
            ], domain_expand])
        else:
            domain_expand = expression.AND([[
                ('project_id', '!=', False),
            ], domain_expand])
        return domain_expand

    @api.model
    def _group_expand_project_ids(self, projects, domain):
        start_date = self._context.get('gantt_start_date')
        scale = self._context.get('gantt_scale')
        default_project_id = self._context.get('default_project_id')
        is_my_task = not self._context.get('all_task')
        if not (start_date and scale) or default_project_id:
            return projects
        domain = self._expand_domain_dates(domain)
        # Check on filtered domain is necessary in case we are in the 'All tasks' menu
        # Indeed, the project_id != False default search would lead in a wrong result when
        # no other search have been made
        filtered_domain = filter_domain_leaf(domain, lambda field: field == "project_id")
        search_on_comodel = self._search_on_comodel(domain, "project_id", "project.project")
        if search_on_comodel and (default_project_id or is_my_task or len(filtered_domain) > 1):
            return search_on_comodel
        return self.search(domain).project_id

    @api.model
    def _group_expand_partner_ids(self, partners, domain):
        start_date = self._context.get('gantt_start_date')
        scale = self._context.get('gantt_scale')
        if not (start_date and scale):
            return partners
        domain = self._expand_domain_dates(domain)
        search_on_comodel = self._search_on_comodel(domain, "partner_id", "res.partner")
        if search_on_comodel:
            return search_on_comodel
        return self.search(domain).partner_id

    def _expand_domain_dates(self, domain):
        filters = []
        for dom in domain:
            if len(dom) == 3 and dom[0] == 'date_deadline' and dom[1] == '>=':
                min_date = dom[2] if isinstance(dom[2], datetime) else datetime.strptime(dom[2], '%Y-%m-%d %H:%M:%S')
                min_date = min_date - get_timedelta(1, self._context.get('gantt_scale'))
                filters.append((dom[0], dom[1], min_date))
            else:
                filters.append(dom)
        return filters

    # -------------------------------------
    # Business Methods : Smart Scheduling
    # -------------------------------------
    def schedule_tasks(self, vals):
        """ Compute the start and end planned date for each task in the recordset.

            This computation is made according to the schedule of the employee the tasks
            are assigned to, as well as the task already planned for the user.
            The function schedules the tasks order by dependencies, priority.
            The transitivity of the tasks is respected in the recordset, but is not guaranteed
            once the tasks are planned for some specific use case. This function ensures that
            no tasks planned by it are concurrent with another.
            If this function is used to plan tasks for the company and not an employee,
            the tasks are planned with the company calendar, and have the same starting date.
            Their end date is computed based on their timesheet only.
            Concurrent or dependent tasks are irrelevant.

            :return: empty dict if some data were missing for the computation
                or if no action and no warning to display.
                Else, return a dict { 'action': action, 'warnings'; warning_list } where action is
                the action to launch if some planification need the user confirmation to be applied,
                and warning_list the warning message to show if needed.
        """
        required_written_fields = {'planned_date_begin', 'date_deadline'}
        if not self.env.context.get('last_date_view') or any(key not in vals for key in required_written_fields):
            self.write(vals)
            return {}

        return self.sorted(
            lambda t: (not t.date_deadline, t.date_deadline, t._get_hours_to_plan() <= 0, -int(t.priority))
        )._scheduling(vals)

    def _scheduling(self, vals):
        tasks_to_write = {}
        warnings = {}
        old_vals_per_task_id = {}

        company = self.company_id if len(self.company_id) == 1 else self.env.company
        tz_info = self._context.get('tz') or 'UTC'

        user_to_assign = self.env['res.users']

        users = self.user_ids
        if vals.get('user_ids') and len(vals['user_ids']) == 1:
            user_to_assign = self.env['res.users'].browse(vals['user_ids'])
            if user_to_assign not in users:
                users |= user_to_assign
            tz_info = user_to_assign.tz or tz_info
        else:
            if (self.env.context.get("default_project_id")):
                project = self.env['project.project'].browse(self.env.context["default_project_id"])
                company = project.company_id if project.company_id else company
                calendar = project.resource_calendar_id
            else:
                calendar = company.resource_calendar_id
            tz_info = calendar.tz or tz_info

        max_date_start = datetime.strptime(self.env.context.get('last_date_view'), '%Y-%m-%d %H:%M:%S').astimezone(timezone(tz_info))
        date_start = datetime.strptime(vals["planned_date_begin"], '%Y-%m-%d %H:%M:%S').astimezone(timezone(tz_info))
        fetch_date_end = max_date_start
        end_loop = date_start + relativedelta(day=31, month=12, years=1)  # end_loop will be the end of the next year.

        valid_intervals_per_user = self._web_gantt_get_valid_intervals(date_start, fetch_date_end, users, [], True)
        dependent_tasks_end_dates = self._fetch_last_date_end_from_dependent_task_for_all_tasks(tz_info)

        scale = self._context.get("gantt_scale", "week")
        # In week and month scale, the precision set is used. In day scale we force the half day precison.
        cell_part_from_context = self._context.get("cell_part")
        cell_part = cell_part_from_context if scale in ["week", "month"] and cell_part_from_context in [1, 2, 4] else 2
        # In year scale, cells represent a month, a typical full-time work schedule involves around 160 to 176 hours per month
        delta_hours = 160 if scale == "year" else 24 / cell_part

        dependencies_dict = {  # contains a task as key and the list of tasks before this one as values
            task:
                [t for t in self if t != task and t in task.depend_on_ids]
                if task.depend_on_ids
                else []
            for task in self
        }
        sorted_tasks = topological_sort(dependencies_dict)

        def update_used_intervals(valid_intervals_per_user, intervals, user_ids):
            used_intervals = Intervals(intervals)
            if not user_ids:
                valid_intervals_per_user[False] -= used_intervals
            else:
                for user_id in valid_intervals_per_user:
                    if not user_id:
                        continue

                    if set(user_id) & set(user_ids):
                        valid_intervals_per_user[user_id] -= used_intervals

        for task in sorted_tasks:
            hours_to_plan = task._get_hours_to_plan()
            if hours_to_plan <= 0:
                hours_to_plan = delta_hours

            compute_date_start = compute_date_end = False
            first_possible_start_date = dependent_tasks_end_dates.get(task.id)

            user_ids = False
            if user_to_assign and user_to_assign not in task.user_ids:
                user_ids = tuple(user_to_assign.ids)
            elif task.user_ids:
                user_ids = tuple(task.user_ids.ids)

            if user_ids not in valid_intervals_per_user:
                if 'no_intervals' not in warnings:
                    warnings['no_intervals'] = _("Some tasks weren't planned because the closest available starting date was too far ahead in the future")
                continue

            temp_valid_intervals_per_user = valid_intervals_per_user.copy()
            used_intervals = []
            while not compute_date_end or hours_to_plan > 0:
                for start_date, end_date, dummy in temp_valid_intervals_per_user[user_ids]:
                    if first_possible_start_date and end_date <= first_possible_start_date:
                        continue

                    hours_to_plan -= (end_date - start_date).total_seconds() / 3600
                    if not compute_date_start:
                        compute_date_start = start_date

                    if hours_to_plan <= 0:
                        compute_date_end = end_date + relativedelta(seconds=hours_to_plan * 3600)
                        used_intervals.append((start_date, compute_date_end, task))
                        break

                    used_intervals.append((start_date, end_date, task))

                # Get more intervals if the fetched ones are not enough for scheduling
                if compute_date_end and hours_to_plan <= 0:
                    break

                if fetch_date_end < end_loop:
                    new_fetch_date_end = min(fetch_date_end + relativedelta(months=1), end_loop)
                    valid_intervals_per_user = self._web_gantt_get_valid_intervals(fetch_date_end, new_fetch_date_end, users, [], True, valid_intervals_per_user)
                    temp_valid_intervals_per_user = valid_intervals_per_user.copy()
                    fetch_date_end = new_fetch_date_end
                    update_used_intervals(temp_valid_intervals_per_user, used_intervals, user_ids)
                else:
                    if 'no_intervals' not in warnings:
                        warnings['no_intervals'] = _("Some tasks weren't planned because the closest available starting date was too far ahead in the future")
                    break

            # remove the task from the record to avoid unnecessary write
            self -= task
            if not compute_date_end or hours_to_plan > 0:
                continue

            start_no_utc = compute_date_start.astimezone(utc).replace(tzinfo=None)
            end_no_utc = compute_date_end.astimezone(utc).replace(tzinfo=None)
            # if the working interval for the task has overlap with 'invalid_intervals', we set the warning message accordingly
            tasks_to_write[task] = {'start': start_no_utc, 'end': end_no_utc}

            for next_task in task.dependent_ids:
                dependent_tasks_end_dates[next_task.id] = max(dependent_tasks_end_dates.get(next_task.id, compute_date_end), compute_date_end)

            update_used_intervals(valid_intervals_per_user, used_intervals, user_ids)

        for task in tasks_to_write:
            old_vals_per_task_id[task.id] = {
                'planned_date_begin': task.planned_date_begin,
                'date_deadline': task.date_deadline,
            }
            task_vals = {
                'planned_date_begin': tasks_to_write[task]['start'],
                'date_deadline': tasks_to_write[task]['end'],
            }
            if user_to_assign:
                old_user_ids = task.user_ids.ids
                if user_to_assign.id not in old_user_ids:
                    task_vals['user_ids'] = user_to_assign.ids
                    old_vals_per_task_id[task.id]['user_ids'] = old_user_ids or False

            task.write(task_vals)

        return [warnings, old_vals_per_task_id]

    def action_rollback_auto_scheduling(self, old_vals_per_task_id):
        for task in self:
            if str(task.id) in old_vals_per_task_id:
                task.write(old_vals_per_task_id[str(task.id)])

    def _get_hours_to_plan(self):
        return self.allocated_hours

    @api.model
    def _compute_schedule(self, user, calendar, date_start, date_end, company=None):
        """ Compute the working intervals available for the employee
            fill the empty schedule slot between contract with the company schedule.
        """
        if user:
            employees_work_days_data, dummy = user.sudo()._get_valid_work_intervals(date_start, date_end)
            schedule = employees_work_days_data.get(user.id) or Intervals([])
            # We are using this function to get the intervals for which the schedule of the employee is invalid. Those data are needed to check if we must fallback on the
            # company schedule. The validity_intervals['valid'] does not contain the work intervals needed, it simply contains large intervals with validity time period
            # ex of return value : ['valid'] = 01-01-2000 00:00:00 to 11-01-2000 23:59:59; ['invalid'] = 11-02-2000 00:00:00 to 12-31-2000 23:59:59
            dummy, validity_intervals = self._web_gantt_reschedule_get_resource_calendars_validity(
                date_start, date_end,
                resource=user._get_project_task_resource(),
                company=company)
            for start, stop, dummy in validity_intervals['invalid']:
                schedule |= calendar._work_intervals_batch(start, stop)[False]

            return validity_intervals['invalid'], schedule
        else:
            return Intervals([]), calendar._work_intervals_batch(date_start, date_end)[False]

    def _fetch_last_date_end_from_dependent_task_for_all_tasks(self, tz_info):
        """
            return: return a dict with task.id as key, and the latest date end from all the dependent task of that task
        """
        query = """
                    SELECT task.id as id,
                           MAX(depends_on.date_deadline) as date
                      FROM project_task task
                      JOIN task_dependencies_rel rel
                        ON rel.task_id = task.id
                      JOIN project_task depends_on
                        ON depends_on.id not in %s
                       AND depends_on.id = rel.depends_on_id
                       AND depends_on.date_deadline is not null
                     WHERE task.id = any(%s)
                  GROUP BY task.id
                """
        self.env.cr.execute(query, [tuple(self.ids), self.ids])
        return {res['id']: res['date'].astimezone(timezone(tz_info)) for res in self.env.cr.dictfetchall()}

    @api.model
    def _fetch_concurrent_tasks_intervals_for_employee(self, date_begin, date_end, user, tz_info):
        concurrent_tasks = self.env['project.task']
        domain = [('user_ids', '=', user.id),
            ('date_deadline', '>=', date_begin),
            ('planned_date_begin', '<=', date_end),
        ]

        if user:
            concurrent_tasks = self.env['project.task'].search(
                domain,
                order='date_deadline',
            )

        return Intervals([
            (t.planned_date_begin.astimezone(timezone(tz_info)),
             t.date_deadline.astimezone(timezone(tz_info)),
             t)
            for t in concurrent_tasks
        ])

    def _check_concurrent_tasks(self, date_begin, date_end, concurrent_tasks):
        current_date_end = None
        for start, stop, dummy in concurrent_tasks:
            if start <= date_end and stop >= date_begin:
                current_date_end = stop
            elif start > date_end:
                break
        return current_date_end

    def _get_end_interval(self, date, intervals):
        for start, stop, dummy in intervals:
            if start <= date <= stop:
                return stop
        return date

    # -------------------------------------
    # Business Methods : Auto-shift
    # -------------------------------------
    def _get_tasks_durations(self, users, start_date_field_name, stop_date_field_name):
        """ task duration is computed as the sum of the durations of the intersections between [task planned_date_begin, task date_deadline]
            and valid_intervals of the user (if only one user is assigned) else valid_intervals of the company
        """
        start_date = min(self.mapped(start_date_field_name))
        end_date = max(self.mapped(stop_date_field_name))
        valid_intervals_per_user = self._web_gantt_get_valid_intervals(start_date, end_date, users, [], False)

        duration_per_task = defaultdict(int)
        for task in self:
            if task.allocated_hours > 0:
                duration_per_task[task.id] = task.allocated_hours * 3600
                continue

            task_start, task_end = task[start_date_field_name].astimezone(utc), task[stop_date_field_name].astimezone(utc)
            user_id = (task.user_ids.id, ) if len(task.user_ids) == 1 else False
            work_intervals = valid_intervals_per_user.get(user_id, Intervals())
            for start, end, dummy in work_intervals:
                start, end = start.astimezone(utc), end.astimezone(utc)
                if task_start < end and task_end > start:
                    duration_per_task[task.id] += (min(task_end, end) - max(task_start, start)).total_seconds()

            if task.id not in duration_per_task:
                duration_per_task[task.id] = (task.date_deadline - task.planned_date_begin).total_seconds()

        return duration_per_task

    def _web_gantt_reschedule_get_resource(self):
        """ Get the resource linked to the task. """
        self.ensure_one()
        return self.user_ids._get_project_task_resource() if len(self.user_ids) == 1 else self.env['resource.resource']

    def _web_gantt_reschedule_get_resource_entity(self):
        """ Get the resource entity linked to the task.
            The resource entity is either a company, either a resource to cope with resource invalidity
            (i.e. not under contract, not yet created...)
            This is used as key to keep information in the rescheduling business methods.
        """
        self.ensure_one()
        return self._web_gantt_reschedule_get_resource() or self.company_id or self.project_id.company_id

    def _web_gantt_reschedule_get_resource_calendars_validity(
            self, date_start, date_end, intervals_to_search=None, resource=None, company=None
    ):
        """ Get the calendars and resources (for instance to later get the work intervals for the provided date_start
            and date_end).

            :param date_start: A start date for the search
            :param date_end: A end date fot the search
            :param intervals_to_search: If given, the periods for which the calendars validity must be retrieved.
            :param resource: If given, it overrides the resource in self._get_resource
            :return: a dict `resource_calendar_validity` with calendars as keys and their validity as values,
                     a dict `resource_validity` with 'valid' and 'invalid' keys, with the intervals where the resource
                     has a valid calendar (resp. no calendar)
            :rtype: tuple(defaultdict(), dict())
        """
        interval = Intervals([(date_start, date_end, self.env['resource.calendar.attendance'])])
        if intervals_to_search:
            interval &= intervals_to_search
        invalid_interval = interval
        resource = self._web_gantt_reschedule_get_resource() if resource is None else resource
        default_company = company or self.company_id or self.project_id.company_id
        resource_calendar_validity = resource.sudo()._get_calendars_validity_within_period(
            date_start, date_end, default_company=default_company
        )[resource.id]
        for calendar in resource_calendar_validity:
            resource_calendar_validity[calendar] &= interval
            invalid_interval -= resource_calendar_validity[calendar]
        resource_validity = {
            'valid': interval - invalid_interval,
            'invalid': invalid_interval,
        }
        return resource_calendar_validity, resource_validity

    def _web_gantt_get_users_unavailable_intervals(self, user_ids, date_begin, date_end, tasks_to_exclude_ids):
        """ Get the unavailable intervals per user, intervals already occupied by other tasks

            :param user_ids: users ids
            :param date_begin: date begin
            :param date_end: date end
            :param tasks_to_exclude_ids: tasks to exclude ids
            :return dict = {user_id: List[Interval]}
        """
        domain = [('user_ids', 'in', user_ids),
            ('date_deadline', '>=', date_begin),
            ('planned_date_begin', '<=', date_end),
        ]

        if tasks_to_exclude_ids:
            domain.append(('id', 'not in', tasks_to_exclude_ids))

        already_planned_tasks = self.env['project.task'].search(domain, order='date_deadline')
        unavailable_intervals_per_user_id = defaultdict(list)
        for task in already_planned_tasks:
            interval_vals = (
                task.planned_date_begin.astimezone(utc),
                task.date_deadline.astimezone(utc),
                task
            )
            for user_id in task.user_ids.ids:
                unavailable_intervals_per_user_id[user_id].append(interval_vals)

        return {user_id: Intervals(vals) for user_id, vals in unavailable_intervals_per_user_id.items()}

    def _web_gantt_get_valid_intervals(self, start_date, end_date, users, candidates_ids=[], remove_intervals_with_planned_tasks=True, valid_intervals_per_user=None):
        """ Get the valid (intervals available for planning)

            :param start_date: start date
            :param end_date: end date end
            :param users: users
            :param candidates_ids: candidates to plan ids
            :param remove_intervals_with_planned_tasks: True to remove the intervals with already planned tasks
            :return (valid intervals dict = {user_id: List[Interval]}, invalid intervals dict = {user_id: List[Interval]})
        """
        start_date, end_date = start_date.astimezone(utc), end_date.astimezone(utc)
        users_work_intervals, calendar_work_intervals = users._get_valid_work_intervals(start_date, end_date)
        unavailable_intervals = self._web_gantt_get_users_unavailable_intervals(users.ids, start_date, end_date, candidates_ids) if remove_intervals_with_planned_tasks else {}
        baseInterval = Intervals([(start_date, end_date, self.env['resource.calendar.attendance'])])
        new_valid_intervals_per_user = {}
        invalid_intervals_per_user = {}
        for user_id, work_intervals in users_work_intervals.items():
            _id = (user_id,)
            new_valid_intervals_per_user[_id] = work_intervals - unavailable_intervals.get(user_id, Intervals())
            invalid_intervals_per_user[_id] = baseInterval - new_valid_intervals_per_user[_id]

        company_id = users.company_id if len(users.company_id) == 1 else self.env.company
        company_calendar_id = company_id.resource_calendar_id
        company_work_intervals = calendar_work_intervals.get(company_calendar_id.id)
        if not company_work_intervals:
            new_valid_intervals_per_user[False] = company_calendar_id._work_intervals_batch(start_date, end_date)[False]
        else:
            new_valid_intervals_per_user[False] = company_work_intervals

        for task in self:
            user_ids = tuple(task.user_ids.ids)
            if len(user_ids) < 2 or user_ids in new_valid_intervals_per_user:
                continue

            new_valid_intervals_per_user[user_ids] = new_valid_intervals_per_user[False]
            for user_id in user_ids:
                # if user is not present in invalid_intervals => he's not present in users_work_intervals
                # => he's not available at all and the users together don't have any valid interval in commun
                if (user_id, ) not in invalid_intervals_per_user:
                    new_valid_intervals_per_user[user_ids] = Intervals()
                    break

                new_valid_intervals_per_user[user_ids] -= invalid_intervals_per_user.get((user_id, ))

        if not valid_intervals_per_user:
            valid_intervals_per_user = new_valid_intervals_per_user
        else:
            for user_ids in new_valid_intervals_per_user:
                if user_ids in valid_intervals_per_user:
                    valid_intervals_per_user[user_ids] |= new_valid_intervals_per_user[user_ids]
                else:
                    valid_intervals_per_user[user_ids] = new_valid_intervals_per_user[user_ids]

        return valid_intervals_per_user

    def _web_gantt_move_candidates(self, start_date_field_name, stop_date_field_name, dependency_field_name, dependency_inverted_field_name, search_forward, candidates_ids, date_candidate=None, all_candidates_ids=None, move_not_in_conflicts_candidates=False):
        result = {
            "errors": [],
            "warnings": [],
        }
        old_vals_per_pill_id = {}
        candidates = self.browse(candidates_ids)
        all_candidates = self.browse(all_candidates_ids or candidates_ids)
        users = candidates.user_ids.sudo()
        self_dependency_field_name = self[dependency_field_name if search_forward else dependency_inverted_field_name]

        if search_forward:
            start_date = date_candidate or max((self_dependency_field_name.filtered(stop_date_field_name and start_date_field_name) - candidates).mapped(stop_date_field_name))
            # 53 weeks = 1 year is estimated enough to plan a project (no valid proof)
            end_date = start_date + timedelta(weeks=53)
        else:
            end_date = date_candidate or min((self_dependency_field_name.filtered(stop_date_field_name and start_date_field_name) - candidates).mapped(start_date_field_name))
            start_date = max(datetime.now(), end_date - timedelta(weeks=53))
            if end_date <= start_date:
                result["errors"].append("past_error")
                return result, {}

        valid_intervals_per_user = candidates._web_gantt_get_valid_intervals(start_date, end_date, users, all_candidates.ids or candidates.ids)
        initial_valid_intervals_per_user = dict(valid_intervals_per_user.items())
        move_in_conflicts_users = set()
        first_possible_start_date_per_candidate = {}
        last_possible_end_date_per_candidate = {}

        for candidate in candidates:
            related_candidates = candidate[dependency_field_name] if search_forward else candidate[dependency_inverted_field_name]
            replanned_candidates = related_candidates.filtered(lambda x: x in candidates)

            # this line is used when planning without conflicts we do it in 2 steps, so all_candidates contains all the tasks to replan and candidates contains the task to replan in the current step
            all_replanned_candidates = related_candidates.filtered(lambda x: x in all_candidates)
            not_replanned_candidates = related_candidates - all_replanned_candidates

            if not not_replanned_candidates:
                continue

            boundary_date = stop_date_field_name if search_forward else start_date_field_name
            boundary_dates = not_replanned_candidates.filtered(boundary_date).mapped(boundary_date)

            if not boundary_dates:
                continue

            if search_forward:
                first_possible_start_date_per_candidate[candidate.id] = max(boundary_dates).astimezone(utc)
            else:
                last_possible_end_date_per_candidate[candidate.id] = min(boundary_dates).astimezone(utc)

        step = 1 if search_forward else -1
        candidates_moved_with_conflicts = False
        candidates_passed_initial_deadline = False
        candidates_durations = candidates._get_tasks_durations(users, start_date_field_name, stop_date_field_name)

        for candidate in candidates:
            if not move_not_in_conflicts_candidates and not candidate._web_gantt_is_candidate_in_conflict(start_date_field_name, stop_date_field_name, dependency_field_name, dependency_inverted_field_name):
                continue

            candidate_duration = candidates_durations[candidate.id]
            users = candidate.user_ids
            users_ids = tuple(users.ids) if users else False

            if users_ids not in valid_intervals_per_user:
                result["errors"].append("no_intervals_error")
                return result, {}

            intervals = valid_intervals_per_user[users_ids]._items
            intervals_durations = 0
            index = 0 if search_forward else len(intervals) - 1
            used_intervals = []
            compute_start_date, compute_end_date = False, False
            while users_ids not in move_in_conflicts_users and ((search_forward and index < len(intervals)) or (not search_forward and index >= 0)) and candidate_duration > intervals_durations:
                start, end, _dummy = intervals[index]
                index += step
                start, end = start.astimezone(utc), end.astimezone(utc)

                if search_forward:
                    first_date = first_possible_start_date_per_candidate.get(candidate.id)
                    if first_date and end <= first_date:
                        continue

                    if not compute_start_date:
                        if first_date:
                            start = max(start, first_date)
                        compute_start_date = start

                    compute_end_date = end
                else:
                    last_date = last_possible_end_date_per_candidate.get(candidate.id)
                    if last_date and start >= last_date:
                        continue

                    if not compute_end_date:
                        if last_date:
                            end = min(end, last_date)
                        compute_end_date = end

                    compute_start_date = start

                duration = (end - start).total_seconds()
                if intervals_durations + duration > candidate_duration:
                    remaining = intervals_durations + duration - candidate_duration
                    duration -= remaining
                    if search_forward:
                        end += timedelta(seconds=-remaining)
                        compute_end_date = end
                    else:
                        start += timedelta(seconds=remaining)
                        compute_start_date = start

                intervals_durations += duration
                used_intervals.append((start, end, candidate))

            if users_ids not in move_in_conflicts_users and candidate_duration == intervals_durations and compute_start_date and compute_end_date:
                candidates_passed_initial_deadline = candidates_passed_initial_deadline or (not candidate[start_date_field_name] and compute_end_date > candidate[stop_date_field_name].astimezone(utc))
                old_planned_date_begin, old_date_deadline = candidate[start_date_field_name], candidate[stop_date_field_name]
                if candidate._web_gantt_reschedule_write_new_dates(compute_start_date, compute_end_date, start_date_field_name, stop_date_field_name):
                    old_vals_per_pill_id[candidate.id] = {
                        "planned_date_begin": old_planned_date_begin,
                        "date_deadline": old_date_deadline,
                    }
                else:
                    result["errors"].append("past_error")
                    return result, {}
            else:
                """ no more intervals and we haven't reached the duration to plan the candidate (pill)
                    plan in the first interval, this will lead to creating conflicts, so a notif is added
                    to notify the user
                """
                if users_ids not in initial_valid_intervals_per_user or len(initial_valid_intervals_per_user[users_ids]._items) == 0:
                    result["errors"].append("no_intervals_error")
                    return result, {}

                candidates_moved_with_conflicts = True
                move_in_conflicts_users.add(users_ids)
                final_interval_index = -1 if search_forward else 0
                ranges = initial_valid_intervals_per_user[users_ids]._items
                compute_start_date = ranges[final_interval_index][0]
                compute_end_date = ranges[final_interval_index][1]
                needed_intervals_duration = 0
                searching_step = -1 if search_forward else 1
                searching_index = len(ranges) if search_forward else -1
                while ((search_forward and searching_index - 1 > 0) or (not search_forward and searching_index + 1 < len(ranges))) and candidate_duration > needed_intervals_duration:
                    searching_index += searching_step
                    start, end, _dummy = ranges[searching_index]
                    start, end = start.astimezone(utc), end.astimezone(utc)
                    if search_forward:
                        compute_start_date = start
                    else:
                        compute_end_date = end

                    needed_intervals_duration += (end - start).total_seconds()

                if candidate_duration <= needed_intervals_duration:
                    remaining = needed_intervals_duration - candidate_duration

                    if search_forward:
                        compute_start_date += timedelta(seconds=remaining)
                    else:
                        compute_end_date += timedelta(seconds=-remaining)
                old_planned_date_begin, old_date_deadline = candidate[start_date_field_name], candidate[stop_date_field_name]
                if candidate._web_gantt_reschedule_write_new_dates(compute_start_date, compute_end_date, start_date_field_name, stop_date_field_name):
                    old_vals_per_pill_id[candidate.id] = {
                        "planned_date_begin": old_planned_date_begin,
                        "date_deadline": old_date_deadline,
                    }
                else:
                    result["errors"].append("past_error")
                    return result, {}

            next_candidates = candidate[dependency_inverted_field_name if search_forward else dependency_field_name]
            for task in next_candidates:
                if not task._web_gantt_reschedule_is_record_candidate(start_date_field_name, stop_date_field_name):
                    continue

                if search_forward:
                    candidate_date = max(first_possible_start_date_per_candidate[task.id], compute_end_date) if first_possible_start_date_per_candidate.get(task.id) else compute_end_date
                    first_possible_start_date_per_candidate[task.id] = candidate_date
                else:
                    candidate_date = min(last_possible_end_date_per_candidate[task.id], compute_start_date) if last_possible_end_date_per_candidate.get(task.id) else compute_start_date
                    last_possible_end_date_per_candidate[task.id] = candidate_date

            used_intervals = Intervals(used_intervals)
            if not users_ids:
                valid_intervals_per_user[False] -= used_intervals
            else:
                for user in valid_intervals_per_user:
                    if not user:
                        continue

                    if set(user) & set(users_ids):
                        valid_intervals_per_user[user] -= used_intervals

        if candidates_passed_initial_deadline:
            result["warnings"].append("initial_deadline")
        if candidates_moved_with_conflicts:
            result["warnings"].append("conflict")
        return result, old_vals_per_pill_id

    def _web_gantt_reschedule_is_record_candidate(self, start_date_field_name, stop_date_field_name):
        """ Get whether the record is a candidate for the rescheduling. This method is meant to be overridden when
            we need to add a constraint in order to prevent some records to be rescheduled. This method focuses on the
            record itself (if you need to have information on the relation (master and slave) rather override
            _web_gantt_reschedule_is_relation_candidate).

            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :return: True if record can be rescheduled, False if not.
            :rtype: bool
        """
        self.ensure_one()
        return self[start_date_field_name] and self[stop_date_field_name] and self.project_id.allow_task_dependencies and not self.is_closed

    def _web_gantt_get_reschedule_message_per_key(self, key, params=None):
        message = super()._web_gantt_get_reschedule_message_per_key(key, params)
        if message:
            return message

        if key == "no_intervals_error":
            return _("The tasks could not be rescheduled due to the assignees' lack of availability at this time.")
        elif key == "initial_deadline":
            return _("Some tasks were planned after their initial deadline.")
        elif key == "conflict":
            return _("Some tasks were scheduled concurrently, resulting in a conflict due to the limited availability of the assignees. The planned dates for these tasks may not align with their allocated hours.")
        else:
            return ""

    # ----------------------------------------------------
    # Overlapping tasks
    # ----------------------------------------------------

    def action_fsm_view_overlapping_tasks(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('project.action_view_all_task')
        if 'views' in action:
            gantt_view = self.env.ref("project_enterprise.project_task_dependency_view_gantt")
            map_view = self.env.ref('project_enterprise.project_task_map_view_no_title')
            action['views'] = [(gantt_view.id, 'gantt'), (map_view.id, 'map')] + [(state, view) for state, view in action['views'] if view not in ['gantt', 'map']]
        name = _('Tasks in Conflict')
        action.update({
            'display_name': name,
            'name': name,
            'domain' : [
                ('user_ids', 'in', self.user_ids.ids),
            ],
            'context': {
                'fsm_mode': False,
                'task_nameget_with_hours': False,
                'initialDate': self.planned_date_begin,
                'search_default_conflict_task': True,
            }
        })
        return action

    # ----------------------------------------------------
    # Gantt view
    # ----------------------------------------------------

    @api.model
    def _gantt_unavailability(self, field, res_ids, start, stop, scale):
        resources = self.env['resource.resource']
        if field in ['user_ids', 'user_id']:
            resources = resources.search([('user_id', 'in', res_ids), ('company_id', '=', self.env.company.id)], order='create_date')
        # we reverse sort the resources by date to keep the first one created in the dictionary
        # to anticipate the case of a resource added later for the same employee and company
        user_resource_mapping = {resource.user_id.id: resource.id for resource in resources}
        leaves_mapping = resources._get_unavailable_intervals(start, stop)
        company_calendar = self.env.company.resource_calendar_id
        company_leaves = [] if company_calendar.flexible_hours else company_calendar._unavailable_intervals(start.replace(tzinfo=utc), stop.replace(tzinfo=utc))

        cell_dt = timedelta(hours=1) if scale in ['day', 'week'] else timedelta(hours=12)

        result = {}
        for user_id in res_ids + [False]:
            resource_id = user_resource_mapping.get(user_id)
            calendar = leaves_mapping.get(resource_id, company_leaves)
            # remove intervals smaller than a cell, as they will cause half a cell to turn grey
            # ie: when looking at a week, a employee start everyday at 8, so there is a unavailability
            # like: 2019-05-22 20:00 -> 2019-05-23 08:00 which will make the first half of the 23's cell grey
            notable_intervals = filter(lambda interval: interval[1] - interval[0] >= cell_dt, calendar)
            result[user_id] = [{'start': interval[0], 'stop': interval[1]} for interval in notable_intervals]

        return result

    def web_gantt_write(self, data):
        res = True

        if any(
            f_name in self._fields and self._fields[f_name].type == 'many2many' and value and len(value) == 1
            for f_name, value in data.items()
        ):
            record_ids_per_m2m_field_names = defaultdict(list)
            full_write_record_ids = []
            for record in self:
                fields_to_remove = []
                for f_name, value in data.items():
                    if (
                        value
                        and f_name in record._fields
                        and record._fields[f_name].type == 'many2many'
                        and len(value) == 1
                        and value[0] in record[f_name].ids
                    ):
                        fields_to_remove.append(f_name)
                if fields_to_remove:
                    record_ids_per_m2m_field_names[tuple(fields_to_remove)].append(record.id)
                else:
                    full_write_record_ids.append(record.id)
            if record_ids_per_m2m_field_names:
                if full_write_record_ids:
                    res &= self.browse(full_write_record_ids).write(data)
                for fields_to_remove_from_data, record_ids in record_ids_per_m2m_field_names.items():
                    res &= self.browse(record_ids).write({
                        f_name: value
                        for f_name, value in data.items()
                        if f_name not in fields_to_remove_from_data
                    })
            else:
                res &= self.write(data)
        else:
            res &= self.write(data)

        return res

    def action_dependent_tasks(self):
        action = super().action_dependent_tasks()
        action['view_mode'] = 'list,form,kanban,calendar,pivot,graph,gantt,activity,map'
        return action

    def action_recurring_tasks(self):
        action = super().action_recurring_tasks()
        action['view_mode'] = 'list,form,kanban,calendar,pivot,graph,gantt,activity,map'
        return action

    def _gantt_progress_bar_user_ids(self, res_ids, start, stop):
        start_naive, stop_naive = start.replace(tzinfo=None), stop.replace(tzinfo=None)
        users = self.env['res.users'].search([('id', 'in', res_ids)])
        self.env['project.task'].check_access('read')

        project_tasks = self.env['project.task'].sudo().search([
            ('user_ids', 'in', res_ids),
            ('planned_date_begin', '<=', stop_naive),
            ('date_deadline', '>=', start_naive),
        ])
        project_tasks = project_tasks.with_context(prefetch_fields=False)
        # Prefetch fields from database to avoid doing one query by __get__.
        project_tasks.fetch(['planned_date_begin', 'date_deadline', 'user_ids'])
        allocated_hours_mapped = defaultdict(float)
        # Get the users work intervals between start and end dates of the gantt view
        users_work_intervals, dummy = users.sudo()._get_valid_work_intervals(start, stop)
        allocated_hours_mapped = project_tasks._allocated_hours_per_user_for_scale(users, start, stop)
        # Compute employee work hours based on its work intervals.
        work_hours = {
            user_id: sum_intervals(work_intervals)
            for user_id, work_intervals in users_work_intervals.items()
        }
        return {
            user.id: {
                'value': allocated_hours_mapped[user.id],
                'max_value': work_hours.get(user.id, 0.0),
            }
            for user in users
        }

    def _allocated_hours_per_user_for_scale(self, users, start, stop):
        absolute_max_end, absolute_min_start = stop, start
        allocated_hours_mapped = defaultdict(float)
        for task in self:
            absolute_max_end = max(absolute_max_end, utc.localize(task.date_deadline))
            absolute_min_start = min(absolute_min_start, utc.localize(task.planned_date_begin))
        users_work_intervals, _dummy = users.sudo()._get_valid_work_intervals(absolute_min_start, absolute_max_end)
        for task in self:
            task_date_begin = utc.localize(task.planned_date_begin)
            task_deadline = utc.localize(task.date_deadline)
            max_start = max(start, task_date_begin)
            min_end = min(stop, task_deadline)
            for user in task.user_ids:
                work_intervals_for_scale = sum_intervals(users_work_intervals[user.id] & Intervals([(max_start, min_end, self.env['resource.calendar.attendance'])]))
                work_intervals_for_task = sum_intervals(users_work_intervals[user.id] & Intervals([(task_date_begin, task_deadline, self.env['resource.calendar.attendance'])]))
                # The ratio between the workable hours in the gantt view scale and the workable hours
                # between start and end dates of the task allows to determine the allocated hours for the current scale
                ratio = 1
                if work_intervals_for_task:
                    ratio = work_intervals_for_scale / work_intervals_for_task
                allocated_hours_mapped[user.id] += (task.allocated_hours / len(task.user_ids)) * ratio

        return allocated_hours_mapped

    def _gantt_progress_bar(self, field, res_ids, start, stop):
        if not self.env.user.has_group("project.group_project_user"):
            return {}
        if field == 'user_ids':
            start, stop = utc.localize(start), utc.localize(stop)
            return dict(
                self._gantt_progress_bar_user_ids(res_ids, start, stop),
                warning=_("This user isn't expected to have any tasks assigned during this period because they don't have any running contract."),
            )
        raise NotImplementedError(_("This Progress Bar is not implemented."))

    @api.model
    @api.readonly
    def get_all_deadlines(self, date_start, date_end):
        """ Get all deadlines (milestones and projects) between date_start and date_end.

            :param date_start: The start date.
            :param date_end: The end date.

            :return: A dictionary with the field_name of tasks as key and list of records.
        """
        results = {}
        project_id = self._context.get('default_project_id', False)
        project_domain = [
            ('date', '>=', date_start),
            ('date_start', '<=', date_end),
        ]
        milestone_domain = [
            ('deadline', '>=', date_start),
            ('deadline', '<=', date_end),
        ]
        if project_id:
            project_domain = expression.AND([project_domain, [('id', '=', project_id)]])
            milestone_domain = expression.AND([milestone_domain, [('project_id', '=', project_id)]])
        results['project_id'] = self.env['project.project'].search_read(
            project_domain,
            ['id', 'name', 'date', 'date_start']
        )
        results['milestone_id'] = self.env['project.milestone'].search_read(
            milestone_domain,
            ['name', 'deadline', 'is_deadline_exceeded', 'is_reached', 'project_id'],
        )
        return results
