# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

import logging
import pytz

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import partition, SQL

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
        return self.env['mail.activity']._default_activity_type_for_model(self._name)

    activity_ids = fields.One2many(
        'mail.activity', 'res_id', 'Activities',
        bypass_search_access=True,
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
        compute='_compute_activity_user_id', readonly=True,
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

    @api.depends('activity_ids.user_id')
    def _compute_activity_user_id(self):
        for record in self:
            record.activity_user_id = record.activity_ids[0].user_id if record.activity_ids else False

    def _search_activity_exception_decoration(self, operator, operand):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
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
        if operator == 'in':
            search_states = set(value)
        elif operator == 'not in':
            search_states = all_states - set(value)
        else:
            return NotImplemented

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

        self.env['mail.activity'].flush_model(['active', 'date_deadline', 'res_model', 'user_id', 'user_tz'])
        query = SQL(
            """(
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
                                    mail_activity.date_deadline - DATE_TRUNC('day', %(today_utc)s AT TIME ZONE COALESCE(mail_activity.user_tz, 'utc'))
                            )))
                            )::INT AS activity_state
                    FROM mail_activity
                    WHERE mail_activity.res_model = %(res_model_table)s AND mail_activity.active = true
                GROUP BY res_id
                ) AS res_record
            WHERE %(search_states_int)s @> ARRAY[activity_state]
            )""",
            today_utc=pytz.utc.localize(datetime.utcnow()),
            res_model_table=self._name,
            search_states_int=list(search_states_int)
        )

        return [('id', 'not in' if reverse_search else 'in', query)]

    @api.depends('activity_ids.date_deadline')
    def _compute_activity_date_deadline(self):
        for record in self:
            activities = record.activity_ids
            record.activity_date_deadline = next(iter(activities), activities).date_deadline

    def _search_activity_date_deadline(self, operator, operand):
        if operator == 'in' and False in operand:
            return Domain('activity_ids', '=', False) | Domain(self._search_activity_date_deadline('in', operand - {False}))
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        return Domain('activity_ids.date_deadline', operator, operand)

    @api.model
    def _search_activity_user_id(self, operator, operand):
        # field supports comparison with any boolean
        domain = Domain.FALSE
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        if operator == 'in':
            bools, values = partition(lambda v: isinstance(v, bool), operand)
            if bools:
                if True in bools:
                    domain |= Domain('activity_ids', '!=', False)
                if False in bools:
                    domain |= Domain('activity_ids', '=', False)
                if not values:
                    return domain
                operand = values
        # basic case
        return domain | Domain('activity_ids', 'any', [('active', 'in', [True, False]), ('user_id', operator, operand)])

    @api.model
    def _search_activity_type_id(self, operator, operand):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        return [('activity_ids.activity_type_id', operator, operand)]

    @api.model
    def _search_activity_summary(self, operator, operand):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
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
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        return [('activity_ids', 'any', [
            ('active', '=', True),  # never overdue if "done"
            ('date_deadline', operator, operand),
            ('res_model', '=', self._name),
            ('user_id', '=', self.env.user.id)
        ])]

    def _read_group_groupby(self, alias, groupby_spec, query):
        if groupby_spec != 'activity_state':
            return super()._read_group_groupby(alias, groupby_spec, query)
        self._check_field_access(self._fields['activity_state'], 'read')

        # if already grouped by activity_state, do not add the join again
        alias = query.make_alias(self._table, 'last_activity_state')
        if alias in query._joins:
            return SQL.identifier(alias, 'activity_state')

        self.env['mail.activity'].flush_model(['res_model', 'res_id', 'user_id', 'date_deadline'])
        self.env['res.users'].flush_model(['partner_id'])
        self.env['res.partner'].flush_model(['tz'])

        tz = 'UTC'
        if self.env.context.get('tz') in pytz.all_timezones_set:
            tz = self.env.context['tz']

        sql_join = SQL(
            """
            (SELECT res_id,
                CASE
                    WHEN min(EXTRACT(day from (mail_activity.date_deadline - DATE_TRUNC('day', %(today_utc)s AT TIME ZONE COALESCE(mail_activity.user_tz, %(tz)s))))) > 0 THEN 'planned'
                    WHEN min(EXTRACT(day from (mail_activity.date_deadline - DATE_TRUNC('day', %(today_utc)s AT TIME ZONE COALESCE(mail_activity.user_tz, %(tz)s))))) < 0 THEN 'overdue'
                    WHEN min(EXTRACT(day from (mail_activity.date_deadline - DATE_TRUNC('day', %(today_utc)s AT TIME ZONE COALESCE(mail_activity.user_tz, %(tz)s))))) = 0 THEN 'today'
                    ELSE null
                END AS activity_state
            FROM mail_activity
            WHERE res_model = %(res_model)s AND mail_activity.active = true
            GROUP BY res_id)
            """,
            res_model=self._name,
            today_utc=pytz.utc.localize(datetime.utcnow()),
            tz=tz,
        )
        alias = query.left_join(self._table, "id", sql_join, "res_id", "last_activity_state")

        return SQL.identifier(alias, 'activity_state')

    # Reschedules next my activity to Today
    def action_reschedule_my_next_today(self):
        self.ensure_one()
        my_next_activity = self.activity_ids.filtered(lambda activity: activity.user_id == self.env.user)[:1]
        my_next_activity.action_reschedule_today()

    # Reschedules next my activity to Tomorrow
    def action_reschedule_my_next_tomorrow(self):
        self.ensure_one()
        my_next_activity = self.activity_ids.filtered(lambda activity: activity.user_id == self.env.user)[:1]
        my_next_activity.action_reschedule_tomorrow()

    # Reschedules next my activity to Next Monday
    def action_reschedule_my_next_nextweek(self):
        self.ensure_one()
        my_next_activity = self.activity_ids.filtered(lambda activity: activity.user_id == self.env.user)[:1]
        my_next_activity.action_reschedule_nextweek()

    def activity_send_mail(self, template_id):
        """ Automatically send an email based on the given mail.template, given
        its ID. """
        template = self.env['mail.template'].browse(template_id).exists()
        if not template:
            return False
        self.message_post_with_source(
            template,
            subtype_xmlid='mail.mt_comment',
        )
        return True

    def activity_search(self, act_type_xmlids='', user_id=None, additional_domain=None, only_automated=True):
        """ Search automated activities on current record set, given a list of activity
        types xml IDs. It is useful when dealing with specific types involved in automatic
        activities management.

        :param act_type_xmlids: list of activity types xml IDs
        :param user_id: if set, restrict to activities of that user_id;
        :param additional_domain: if set, filter on that domain;
        :param only_automated: if unset, search for all activities, not only automated ones;
        """
        if self.env.context.get('mail_activity_automation_skip'):
            return self.env['mail.activity']

        Data = self.env['ir.model.data'].sudo()
        activity_types_ids = [type_id for type_id in (Data._xmlid_to_res_id(xmlid, raise_if_not_found=False) for xmlid in act_type_xmlids) if type_id]
        if not any(activity_types_ids):
            return self.env['mail.activity']

        domain = Domain([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('activity_type_id', 'in', activity_types_ids)
        ])

        if only_automated:
            domain &= Domain('automated', '=', True)
        if user_id:
            domain &= Domain('user_id', '=', user_id)
        if additional_domain:
            domain &= Domain(additional_domain)

        return self.env['mail.activity'].search(domain)

    def activity_schedule(self, act_type_xmlid='', date_deadline=None, summary='', note='', **act_values):
        """ Schedule an activity on each record of the current record set.
        This method allow to provide as parameter act_type_xmlid. This is an
        xml_id of activity type instead of directly giving an activity_type_id.
        It is useful to avoid having various "env.ref" in the code and allow
        to let the mixin handle access rights.

        Note that unless specified otherwise in act_values, the activities created
        will have their "automated" field set to True.

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
            activity_type_id = self.env['ir.model.data']._xmlid_to_res_id(act_type_xmlid, raise_if_not_found=False)
        else:
            activity_type_id = act_values.get('activity_type_id', False)
        activity_type = self.env['mail.activity.type'].browse(activity_type_id)
        invalid_model = activity_type.res_model and activity_type.res_model != self._name
        if not activity_type or invalid_model:
            if invalid_model:
                _logger.warning(
                    'Invalid activity type model %s used on %s (tried with xml id %s)',
                    activity_type.res_model, self._name, act_type_xmlid or '',
                )
            # TODO master: reset invalid model to default type, keep it for stable as not harmful
            if not activity_type:
                activity_type = self._default_activity_type()

        model_id = self.env['ir.model']._get(self._name).id
        create_vals_list = []
        for record in self:
            create_vals = {
                'activity_type_id': activity_type.id,
                'summary': summary or activity_type.summary,
                'automated': True,
                'note': note or activity_type.default_note,
                'date_deadline': date_deadline,
                'res_model_id': model_id,
                'res_id': record.id,
            }
            create_vals.update(act_values)
            if not create_vals.get('user_id') and activity_type.default_user_id:
                create_vals['user_id'] = activity_type.default_user_id.id
            create_vals_list.append(create_vals)
        return self.env['mail.activity'].create(create_vals_list)

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

        view_ref = views_or_xmlid.id if isinstance(views_or_xmlid, models.BaseModel) else views_or_xmlid
        render_context = render_context or dict()
        activities = self.env['mail.activity']
        for record in self:
            render_context['object'] = record
            note = self.env['ir.qweb']._render(view_ref, render_context, minimal_qcontext=True, raise_if_not_found=False)
            activities += record.activity_schedule(act_type_xmlid=act_type_xmlid, date_deadline=date_deadline, summary=summary, note=note, **act_values)
        return activities

    def activity_reschedule(self, act_type_xmlids, user_id=None, date_deadline=None, new_user_id=None, only_automated=True):
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
        activities = self.activity_search(act_type_xmlids, user_id=user_id, only_automated=only_automated)
        if activities:
            write_vals = {}
            if date_deadline:
                write_vals['date_deadline'] = date_deadline
            if new_user_id:
                write_vals['user_id'] = new_user_id
            activities.write(write_vals)
        return activities

    def activity_feedback(self, act_type_xmlids, user_id=None, feedback=None, attachment_ids=None, only_automated=True):
        """ Set activities as done, limiting to some activity types and
        optionally to a given user. """
        if self.env.context.get('mail_activity_automation_skip'):
            return False

        Data = self.env['ir.model.data'].sudo()
        activity_types_ids = [Data._xmlid_to_res_id(xmlid, raise_if_not_found=False) for xmlid in act_type_xmlids]
        activity_types_ids = [act_type_id for act_type_id in activity_types_ids if act_type_id]
        if not any(activity_types_ids):
            return False
        activities = self.activity_search(act_type_xmlids, user_id=user_id, only_automated=only_automated)
        if activities:
            activities.action_feedback(feedback=feedback, attachment_ids=attachment_ids)
        return True

    def activity_unlink(self, act_type_xmlids, user_id=None, only_automated=True):
        """ Unlink activities, limiting to some activity types and optionally
       to a given user. """
        if self.env.context.get('mail_activity_automation_skip'):
            return False

        Data = self.env['ir.model.data'].sudo()
        activity_types_ids = [Data._xmlid_to_res_id(xmlid, raise_if_not_found=False) for xmlid in act_type_xmlids]
        activity_types_ids = [act_type_id for act_type_id in activity_types_ids if act_type_id]
        if not any(activity_types_ids):
            return False
        self.activity_search(act_type_xmlids, user_id=user_id, only_automated=only_automated).unlink()
        return True
