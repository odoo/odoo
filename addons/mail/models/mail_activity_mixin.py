# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

import logging
import pytz

from odoo import api, fields, models
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class MailActivityMixin(models.AbstractModel):
    """ Mail Activity Mixin is a mixin class to use if you want to add activities
    management on a model. It works like the mail.thread mixin. It defines
    an activity_ids one2many field toward activities using res_id and res_model_id.
    Various related / computed fields are also added to have a global status of
    activities on documents.

    Activities come with a new JS widget for the form view. It is integrated in the
    Chatter widget although it is a separate widget. It displays activities linked
    to the current record and allow to schedule, edit and mark done activities.
    Just include field activity_ids in the div.oe-chatter to use it.

    There is also a kanban widget defined. It defines a small widget to integrate
    in kanban vignettes. It allow to manage activities directly from the kanban
    view. Use widget="kanban_activity" on activitiy_ids field in kanban view to
    use it.

    Some context keys allow to control the mixin behavior. Use those in some
    specific cases like import

     * ``mail_activity_automation_skip``: skip activities automation; it means
       no automated activities will be generated, updated or unlinked, allowing
       to save computation and avoid generating unwanted activities;
    """
    _name = 'mail.activity.mixin'
    _description = 'Activity Mixin'

    def _default_activity_type(self):
        """Define a default fallback activity type when requested xml id wasn't found.

        Can be overriden to specify the default activity type of a model.
        It is only called in in activity_schedule() for now.
        """
        return self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False) \
            or self.env['mail.activity.type'].search([('res_model', '=', self._name)], limit=1) \
            or self.env['mail.activity.type'].search([('res_model', '=', False)], limit=1)

    activity_ids = fields.One2many(
        'mail.activity', 'res_id', 'Activities',
        auto_join=True,
        groups="base.group_user",)
    activity_state = fields.Selection([
        ('overdue', 'Overdue'),
        ('today', 'Today'),
        ('planned', 'Planned')], string='Activity State',
        compute='_compute_activity_state',
        search='_search_activity_state',
        groups="base.group_user",
        help='Status based on activities\nOverdue: Due date is already passed\n'
             'Today: Activity date is today\nPlanned: Future activities.')
    activity_user_id = fields.Many2one(
        'res.users', 'Responsible User',
        related='activity_ids.user_id', readonly=False,
        search='_search_activity_user_id',
        groups="base.group_user")
    activity_type_id = fields.Many2one(
        'mail.activity.type', 'Next Activity Type',
        related='activity_ids.activity_type_id', readonly=False,
        search='_search_activity_type_id',
        groups="base.group_user")
    activity_type_icon = fields.Char('Activity Type Icon', related='activity_ids.icon')
    activity_date_deadline = fields.Date(
        'Next Activity Deadline',
        compute='_compute_activity_date_deadline', search='_search_activity_date_deadline',
        compute_sudo=False, readonly=True, store=False,
        groups="base.group_user")
    my_activity_date_deadline = fields.Date(
        'My Activity Deadline',
        compute='_compute_my_activity_date_deadline', search='_search_my_activity_date_deadline',
        compute_sudo=False, readonly=True, groups="base.group_user")
    activity_summary = fields.Char(
        'Next Activity Summary',
        related='activity_ids.summary', readonly=False,
        search='_search_activity_summary',
        groups="base.group_user",)
    activity_exception_decoration = fields.Selection([
        ('warning', 'Alert'),
        ('danger', 'Error')],
        compute='_compute_activity_exception_type',
        search='_search_activity_exception_decoration',
        help="Type of the exception activity on record.")
    activity_exception_icon = fields.Char('Icon', help="Icon to indicate an exception activity.",
        compute='_compute_activity_exception_type')

    @api.depends('activity_ids.activity_type_id.decoration_type', 'activity_ids.activity_type_id.icon')
    def _compute_activity_exception_type(self):
        # prefetch all activity types for all activities, this will avoid any query in loops
        self.mapped('activity_ids.activity_type_id.decoration_type')

        for record in self:
            activity_type_ids = record.activity_ids.mapped('activity_type_id')
            exception_activity_type_id = False
            for activity_type_id in activity_type_ids:
                if activity_type_id.decoration_type == 'danger':
                    exception_activity_type_id = activity_type_id
                    break
                if activity_type_id.decoration_type == 'warning':
                    exception_activity_type_id = activity_type_id
            record.activity_exception_decoration = exception_activity_type_id and exception_activity_type_id.decoration_type
            record.activity_exception_icon = exception_activity_type_id and exception_activity_type_id.icon

    def _search_activity_exception_decoration(self, operator, operand):
        return [('activity_ids.activity_type_id.decoration_type', operator, operand)]

    @api.depends('activity_ids.state')
    def _compute_activity_state(self):
        for record in self:
            states = record.activity_ids.mapped('state')
            if 'overdue' in states:
                record.activity_state = 'overdue'
            elif 'today' in states:
                record.activity_state = 'today'
            elif 'planned' in states:
                record.activity_state = 'planned'
            else:
                record.activity_state = False

    def _search_activity_state(self, operator, value):
        all_states = {'overdue', 'today', 'planned', False}
        if operator == '=':
            search_states = {value}
        elif operator == '!=':
            search_states = all_states - {value}
        elif operator == 'in':
            search_states = set(value)
        elif operator == 'not in':
            search_states = all_states - set(value)

        reverse_search = False
        if False in search_states:
            # If we search "activity_state = False", they might be a lot of records
            # (million for some models), so instead of returning the list of IDs
            # [(id, 'in', ids)] we will reverse the domain and return something like
            # [(id, 'not in', ids)], so the list of ids is as small as possible
            reverse_search = True
            search_states = all_states - search_states

        # Use number in the SQL query for performance purpose
        integer_state_value = {
            'overdue': -1,
            'today': 0,
            'planned': 1,
            False: None,
        }

        search_states_int = {integer_state_value.get(s or False) for s in search_states}

        query = """
          SELECT res_id
            FROM (
                SELECT res_id,
                       -- Global activity state
                       MIN(
                            -- Compute the state of each individual activities
                            -- -1: overdue
                            --  0: today
                            --  1: planned
                           SIGN(EXTRACT(day from (
                                mail_activity.date_deadline - DATE_TRUNC('day', %(today_utc)s AT TIME ZONE res_partner.tz)
                           )))
                        )::INT AS activity_state
                  FROM mail_activity
             LEFT JOIN res_users
                    ON res_users.id = mail_activity.user_id
             LEFT JOIN res_partner
                    ON res_partner.id = res_users.partner_id
                 WHERE mail_activity.res_model = %(res_model_table)s
              GROUP BY res_id
            ) AS res_record
          WHERE %(search_states_int)s @> ARRAY[activity_state]
        """

        self._cr.execute(
            query,
            {
                'today_utc': pytz.utc.localize(datetime.utcnow()),
                'res_model_table': self._name,
                'search_states_int': list(search_states_int)
            },
        )
        return [('id', 'not in' if reverse_search else 'in', [r[0] for r in self._cr.fetchall()])]

    @api.depends('activity_ids.date_deadline')
    def _compute_activity_date_deadline(self):
        for record in self:
            record.activity_date_deadline = record.activity_ids[:1].date_deadline

    def _search_activity_date_deadline(self, operator, operand):
        if operator == '=' and not operand:
            return [('activity_ids', '=', False)]
        return [('activity_ids.date_deadline', operator, operand)]

    @api.model
    def _search_activity_user_id(self, operator, operand):
        return [('activity_ids.user_id', operator, operand)]

    @api.model
    def _search_activity_type_id(self, operator, operand):
        return [('activity_ids.activity_type_id', operator, operand)]

    @api.model
    def _search_activity_summary(self, operator, operand):
        return [('activity_ids.summary', operator, operand)]

    @api.depends('activity_ids.date_deadline', 'activity_ids.user_id')
    @api.depends_context('uid')
    def _compute_my_activity_date_deadline(self):
        for record in self:
            record.my_activity_date_deadline = next((
                activity.date_deadline
                for activity in record.activity_ids
                if activity.user_id.id == record.env.uid
            ), False)

    def _search_my_activity_date_deadline(self, operator, operand):
        activity_ids = self.env['mail.activity']._search([
            ('date_deadline', operator, operand),
            ('res_model', '=', self._name),
            ('user_id', '=', self.env.user.id)
        ])
        return [('activity_ids', 'in', activity_ids)]

    def write(self, vals):
        # Delete activities of archived record.
        if 'active' in vals and vals['active'] is False:
            self.env['mail.activity'].sudo().search(
                [('res_model', '=', self._name), ('res_id', 'in', self.ids)]
            ).unlink()
        return super(MailActivityMixin, self).write(vals)

    def unlink(self):
        """ Override unlink to delete records activities through (res_model, res_id). """
        record_ids = self.ids
        result = super(MailActivityMixin, self).unlink()
        self.env['mail.activity'].sudo().search(
            [('res_model', '=', self._name), ('res_id', 'in', record_ids)]
        ).unlink()
        return result

    def _read_progress_bar(self, domain, group_by, progress_bar):
        group_by_fname = group_by.partition(':')[0]
        if not (progress_bar['field'] == 'activity_state' and self._fields[group_by_fname].store):
            return super()._read_progress_bar(domain, group_by, progress_bar)

        # optimization for 'activity_state'

        # explicitly check access rights, since we bypass the ORM
        self.check_access_rights('read')
        self._flush_search(domain, fields=[group_by_fname], order='id')
        self.env['mail.activity'].flush(['res_model', 'res_id', 'user_id', 'date_deadline'])

        query = self._where_calc(domain)
        self._apply_ir_rules(query, 'read')
        gb = group_by.partition(':')[0]
        annotated_groupbys = [
            self._read_group_process_groupby(gb, query)
            for gb in [group_by, 'activity_state']
        ]
        groupby_dict = {gb['groupby']: gb for gb in annotated_groupbys}
        for gb in annotated_groupbys:
            if gb['field'] == 'activity_state':
                gb['qualified_field'] = '"_last_activity_state"."activity_state"'
        groupby_terms, _orderby_terms = self._read_group_prepare('activity_state', [], annotated_groupbys, query)
        select_terms = [
            '%s as "%s"' % (gb['qualified_field'], gb['groupby'])
            for gb in annotated_groupbys
        ]
        from_clause, where_clause, where_params = query.get_sql()
        tz = self._context.get('tz') or self.env.user.tz or 'UTC'
        select_query = """
            SELECT 1 AS id, count(*) AS "__count", {fields}
            FROM {from_clause}
            JOIN (
                SELECT res_id,
                CASE
                    WHEN min(date_deadline - (now() AT TIME ZONE COALESCE(res_partner.tz, %s))::date) > 0 THEN 'planned'
                    WHEN min(date_deadline - (now() AT TIME ZONE COALESCE(res_partner.tz, %s))::date) < 0 THEN 'overdue'
                    WHEN min(date_deadline - (now() AT TIME ZONE COALESCE(res_partner.tz, %s))::date) = 0 THEN 'today'
                    ELSE null
                END AS activity_state
                FROM mail_activity
                JOIN res_users ON (res_users.id = mail_activity.user_id)
                JOIN res_partner ON (res_partner.id = res_users.partner_id)
                WHERE res_model = '{model}'
                GROUP BY res_id
            ) AS "_last_activity_state" ON ("{table}".id = "_last_activity_state".res_id)
            WHERE {where_clause}
            GROUP BY {group_by}
        """.format(
            fields=', '.join(select_terms),
            from_clause=from_clause,
            model=self._name,
            table=self._table,
            where_clause=where_clause or '1=1',
            group_by=', '.join(groupby_terms),
        )
        num_from_params = from_clause.count('%s')
        where_params[num_from_params:num_from_params] = [tz] * 3 # timezone after from parameters
        self.env.cr.execute(select_query, where_params)
        fetched_data = self.env.cr.dictfetchall()
        self._read_group_resolve_many2x_fields(fetched_data, annotated_groupbys)
        data = [
            {key: self._read_group_prepare_data(key, val, groupby_dict)
             for key, val in row.items()}
            for row in fetched_data
        ]
        return [
            self._read_group_format_result(vals, annotated_groupbys, [group_by], domain)
            for vals in data
        ]

    def toggle_active(self):
        """ Before archiving the record we should also remove its ongoing
        activities. Otherwise they stay in the systray and concerning archived
        records it makes no sense. """
        record_to_deactivate = self.filtered(lambda rec: rec[rec._active_name])
        if record_to_deactivate:
            # use a sudo to bypass every access rights; all activities should be removed
            self.env['mail.activity'].sudo().search([
                ('res_model', '=', self._name),
                ('res_id', 'in', record_to_deactivate.ids)
            ]).unlink()
        return super(MailActivityMixin, self).toggle_active()

    def activity_send_mail(self, template_id):
        """ Automatically send an email based on the given mail.template, given
        its ID. """
        template = self.env['mail.template'].browse(template_id).exists()
        if not template:
            return False
        for record in self:
            record.message_post_with_template(
                template_id,
                composition_mode='comment'
            )
        return True

    def activity_search(self, act_type_xmlids='', user_id=None, additional_domain=None):
        """ Search automated activities on current record set, given a list of activity
        types xml IDs. It is useful when dealing with specific types involved in automatic
        activities management.

        :param act_type_xmlids: list of activity types xml IDs
        :param user_id: if set, restrict to activities of that user_id;
        :param additional_domain: if set, filter on that domain;
        """
        if self.env.context.get('mail_activity_automation_skip'):
            return False

        Data = self.env['ir.model.data'].sudo()
        activity_types_ids = [type_id for type_id in (Data._xmlid_to_res_id(xmlid, raise_if_not_found=False) for xmlid in act_type_xmlids) if type_id]
        if not any(activity_types_ids):
            return False

        domain = [
            '&', '&', '&',
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('automated', '=', True),
            ('activity_type_id', 'in', activity_types_ids)
        ]

        if user_id:
            domain = expression.AND([domain, [('user_id', '=', user_id)]])
        if additional_domain:
            domain = expression.AND([domain, additional_domain])

        return self.env['mail.activity'].search(domain)

    def activity_schedule(self, act_type_xmlid='', date_deadline=None, summary='', note='', **act_values):
        """ Schedule an activity on each record of the current record set.
        This method allow to provide as parameter act_type_xmlid. This is an
        xml_id of activity type instead of directly giving an activity_type_id.
        It is useful to avoid having various "env.ref" in the code and allow
        to let the mixin handle access rights.

        :param date_deadline: the day the activity must be scheduled on
        the timezone of the user must be considered to set the correct deadline
        """
        if self.env.context.get('mail_activity_automation_skip'):
            return False

        if not date_deadline:
            date_deadline = fields.Date.context_today(self)
        if isinstance(date_deadline, datetime):
            _logger.warning("Scheduled deadline should be a date (got %s)", date_deadline)
        if act_type_xmlid:
            activity_type = self.env.ref(act_type_xmlid, raise_if_not_found=False) or self._default_activity_type()
        else:
            activity_type_id = act_values.get('activity_type_id', False)
            activity_type = activity_type_id and self.env['mail.activity.type'].sudo().browse(activity_type_id)

        model_id = self.env['ir.model']._get(self._name).id
        activities = self.env['mail.activity']
        for record in self:
            create_vals = {
                'activity_type_id': activity_type and activity_type.id,
                'summary': summary or activity_type.summary,
                'automated': True,
                'note': note or activity_type.default_note,
                'date_deadline': date_deadline,
                'res_model_id': model_id,
                'res_id': record.id,
                'user_id': act_values.get('user_id') or activity_type.default_user_id.id or self.env.uid
            }
            create_vals.update(act_values)
            activities |= self.env['mail.activity'].create(create_vals)
        return activities

    def _activity_schedule_with_view(self, act_type_xmlid='', date_deadline=None, summary='', views_or_xmlid='', render_context=None, **act_values):
        """ Helper method: Schedule an activity on each record of the current record set.
        This method allow to the same mecanism as `activity_schedule`, but provide
        2 additionnal parameters:
        :param views_or_xmlid: record of ir.ui.view or string representing the xmlid
            of the qweb template to render
        :type views_or_xmlid: string or recordset
        :param render_context: the values required to render the given qweb template
        :type render_context: dict
        """
        if self.env.context.get('mail_activity_automation_skip'):
            return False

        render_context = render_context or dict()
        if isinstance(views_or_xmlid, str):
            views = self.env.ref(views_or_xmlid, raise_if_not_found=False)
        else:
            views = views_or_xmlid
        if not views:
            return
        activities = self.env['mail.activity']
        for record in self:
            render_context['object'] = record
            note = views._render(render_context, engine='ir.qweb', minimal_qcontext=True)
            activities |= record.activity_schedule(act_type_xmlid=act_type_xmlid, date_deadline=date_deadline, summary=summary, note=note, **act_values)
        return activities

    def activity_reschedule(self, act_type_xmlids, user_id=None, date_deadline=None, new_user_id=None):
        """ Reschedule some automated activities. Activities to reschedule are
        selected based on type xml ids and optionally by user. Purpose is to be
        able to

         * update the deadline to date_deadline;
         * update the responsible to new_user_id;
        """
        if self.env.context.get('mail_activity_automation_skip'):
            return False

        Data = self.env['ir.model.data'].sudo()
        activity_types_ids = [Data._xmlid_to_res_id(xmlid, raise_if_not_found=False) for xmlid in act_type_xmlids]
        activity_types_ids = [act_type_id for act_type_id in activity_types_ids if act_type_id]
        if not any(activity_types_ids):
            return False
        activities = self.activity_search(act_type_xmlids, user_id=user_id)
        if activities:
            write_vals = {}
            if date_deadline:
                write_vals['date_deadline'] = date_deadline
            if new_user_id:
                write_vals['user_id'] = new_user_id
            activities.write(write_vals)
        return activities

    def activity_feedback(self, act_type_xmlids, user_id=None, feedback=None):
        """ Set activities as done, limiting to some activity types and
        optionally to a given user. """
        if self.env.context.get('mail_activity_automation_skip'):
            return False

        Data = self.env['ir.model.data'].sudo()
        activity_types_ids = [Data._xmlid_to_res_id(xmlid, raise_if_not_found=False) for xmlid in act_type_xmlids]
        activity_types_ids = [act_type_id for act_type_id in activity_types_ids if act_type_id]
        if not any(activity_types_ids):
            return False
        activities = self.activity_search(act_type_xmlids, user_id=user_id)
        if activities:
            activities.action_feedback(feedback=feedback)
        return True

    def activity_unlink(self, act_type_xmlids, user_id=None):
        """ Unlink activities, limiting to some activity types and optionally
        to a given user. """
        if self.env.context.get('mail_activity_automation_skip'):
            return False

        Data = self.env['ir.model.data'].sudo()
        activity_types_ids = [Data._xmlid_to_res_id(xmlid, raise_if_not_found=False) for xmlid in act_type_xmlids]
        activity_types_ids = [act_type_id for act_type_id in activity_types_ids if act_type_id]
        if not any(activity_types_ids):
            return False
        self.activity_search(act_type_xmlids, user_id=user_id).unlink()
        return True
