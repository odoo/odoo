# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import threading

from datetime import timedelta, date
from ast import literal_eval
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.fields import Datetime
from odoo.exceptions import ValidationError, AccessError
from odoo.osv import expression
from odoo.tools.misc import clean_context

_logger = logging.getLogger(__name__)


class MarketingActivity(models.Model):
    _name = 'marketing.activity'
    _description = 'Marketing Activity'
    _inherit = ['utm.source.mixin']
    _order = 'interval_standardized, id ASC'

    # definition and UTM
    activity_type = fields.Selection([
        ('email', 'Email'),
        ('action', 'Server Action')
        ], string='Activity Type', required=True, default='email')
    mass_mailing_id = fields.Many2one(
        'mailing.mailing', string='Marketing Template', compute='_compute_mass_mailing_id',
        readonly=False, store=True)
    # Technical field doing the mapping of activity type and mailing type
    mass_mailing_id_mailing_type = fields.Selection([
        ('mail', 'Email')], string='Mailing Type', compute='_compute_mass_mailing_id_mailing_type',
        readonly=True, store=True)
    server_action_id = fields.Many2one(
        'ir.actions.server', string='Server Action', compute='_compute_server_action_id',
        readonly=False, store=True)
    campaign_id = fields.Many2one(
        'marketing.campaign', string='Campaign',
        index=True, ondelete='cascade', required=True)
    utm_campaign_id = fields.Many2one(
        'utm.campaign', string='UTM Campaign',
        readonly=True, related='campaign_id.utm_campaign_id')  # propagate to mailings
    # interval
    interval_number = fields.Integer(string='Send after', default=0)
    interval_type = fields.Selection([
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')], string='Delay Type',
        default='hours', required=True)
    interval_standardized = fields.Integer('Send after (in hours)', compute='_compute_interval_standardized', store=True, readonly=True)
    # validity
    validity_duration = fields.Boolean('Validity Duration',
        help='Check this to make sure your actions are not executed after a specific amount of time after the scheduled date. (e.g. Time-limited offer, Upcoming event, …)')
    validity_duration_number = fields.Integer(string='Valid during', default=0)
    validity_duration_type = fields.Selection([
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')],
        default='hours', required=True)
    # target
    domain = fields.Char(
        string='Applied Filter',
        help='Activity will only be performed if record satisfies this domain, obtained from the combination of the activity filter and its inherited filter',
        compute='_compute_inherited_domain', recursive=True, store=True, readonly=True)
    activity_domain = fields.Char(
        string='Activity Filter', default='[]',
        help='Domain that applies to this activity and its child activities')
    model_id = fields.Many2one('ir.model', related='campaign_id.model_id', string='Model', readonly=True)
    model_name = fields.Char(related='model_id.model', string='Model Name', readonly=True)
    # Related to parent activity
    parent_id = fields.Many2one(
        'marketing.activity', string='Activity', compute='_compute_parent_id',
        index=True, readonly=False, store=True, ondelete='cascade')
    allowed_parent_ids = fields.Many2many('marketing.activity', string='Allowed parents', help='All activities which can be the parent of this one', compute='_compute_allowed_parent_ids')
    child_ids = fields.One2many('marketing.activity', 'parent_id', string='Child Activities')
    trigger_type = fields.Selection([
        ('begin', 'beginning of workflow'),
        ('activity', 'another activity'),
        ('mail_open', 'Mail: opened'),
        ('mail_not_open', 'Mail: not opened'),
        ('mail_reply', 'Mail: replied'),
        ('mail_not_reply', 'Mail: not replied'),
        ('mail_click', 'Mail: clicked'),
        ('mail_not_click', 'Mail: not clicked'),
        ('mail_bounce', 'Mail: bounced')], default='begin', required=True)
    trigger_category = fields.Selection([('email', 'Mail')], compute='_compute_trigger_category')
    # cron / updates
    require_sync = fields.Boolean('Require trace sync', copy=False)
    # For trace
    trace_ids = fields.One2many('marketing.trace', 'activity_id', string='Traces', copy=False)
    processed = fields.Integer(compute='_compute_statistics')
    rejected = fields.Integer(compute='_compute_statistics')
    total_sent = fields.Integer(compute='_compute_statistics')
    total_click = fields.Integer(compute='_compute_statistics')
    total_open = fields.Integer(compute='_compute_statistics')
    total_reply = fields.Integer(compute='_compute_statistics')
    total_bounce = fields.Integer(compute='_compute_statistics')
    statistics_graph_data = fields.Char(compute='_compute_statistics_graph_data')
    # activity summary
    activity_summary = fields.Html(string='Activity Summary', compute='_compute_activity_summary')

    @api.constrains('trigger_type', 'parent_id')
    def _check_consistency_in_activities(self):
        """Check the consistency in the activity chaining."""
        for activity in self:
            if (activity.parent_id or activity.allowed_parent_ids) and activity.parent_id not in activity.allowed_parent_ids:
                trigger_string = dict(activity._fields['trigger_type']._description_selection(self.env))[activity.trigger_type]
                raise ValidationError(
                    _('You are trying to set the activity "%(parent_activity)s" as "%(parent_type)s" while its child "%(activity)s" has the trigger type "%(trigger_type)s"\nPlease modify one of those activities before saving.',
                      parent_activity=activity.parent_id.name, parent_type=activity.parent_id.activity_type, activity=activity.name, trigger_type=trigger_string))

    @api.depends('activity_type')
    def _compute_mass_mailing_id_mailing_type(self):
        for activity in self:
            if activity.activity_type == 'email':
                activity.mass_mailing_id_mailing_type = 'mail'
            elif activity.activity_type == 'action':
                activity.mass_mailing_id_mailing_type = False

    @api.depends('mass_mailing_id_mailing_type')
    def _compute_mass_mailing_id(self):
        for activity in self:
            if activity.mass_mailing_id_mailing_type != activity.mass_mailing_id.mailing_type:
                activity.mass_mailing_id = False

    @api.depends('activity_type')
    def _compute_server_action_id(self):
        for activity in self:
            if activity.activity_type != 'action':
                activity.server_action_id = False

    @api.depends('activity_domain', 'campaign_id.domain', 'parent_id.domain')
    def _compute_inherited_domain(self):
        for activity in self:
            domain = expression.AND([literal_eval(activity.activity_domain or '[]'),
                                     literal_eval(activity.campaign_id.domain or '[]')])
            ancestor = activity.parent_id
            while ancestor:
                domain = expression.AND([domain, literal_eval(ancestor.activity_domain or '[]')])
                ancestor = ancestor.parent_id
            activity.domain = domain

    @api.depends('interval_type', 'interval_number')
    def _compute_interval_standardized(self):
        factors = {'hours': 1,
                   'days': 24,
                   'weeks': 168,
                   'months': 720}
        for activity in self:
            activity.interval_standardized = activity.interval_number * factors[activity.interval_type]

    @api.depends('trigger_type')
    def _compute_parent_id(self):
        for activity in self:
            if not activity.parent_id or (activity.parent_id and activity.trigger_type == 'begin'):
                activity.parent_id = False

    @api.depends('trigger_type', 'campaign_id.marketing_activity_ids')
    def _compute_allowed_parent_ids(self):
        for activity in self:
            if activity.trigger_type == 'activity':
                activity.allowed_parent_ids = activity.campaign_id.marketing_activity_ids.filtered(
                    lambda parent_id: parent_id.ids != activity.ids)
            elif activity.trigger_category:
                activity.allowed_parent_ids = activity.campaign_id.marketing_activity_ids.filtered(
                    lambda parent_id: parent_id.ids != activity.ids and parent_id.activity_type == activity.trigger_category)
            else:
                activity.allowed_parent_ids = False

    @api.depends('trigger_type')
    def _compute_trigger_category(self):
        for activity in self:
            if activity.trigger_type in ['mail_open', 'mail_not_open', 'mail_reply', 'mail_not_reply',
                                         'mail_click', 'mail_not_click', 'mail_bounce']:
                activity.trigger_category = 'email'
            else:
                activity.trigger_category = False

    @api.depends('activity_type', 'trace_ids')
    def _compute_statistics(self):
        # Fix after ORM-pocalyspe : Update in any case, otherwise, None to some values (crash)
        self.update({
            'total_bounce': 0, 'total_reply': 0, 'total_sent': 0,
            'rejected': 0, 'total_click': 0, 'processed': 0, 'total_open': 0,
        })
        if self.ids:
            activity_data = {activity._origin.id: {} for activity in self}
            for stat in self._get_full_statistics():
                activity_data[stat.pop('activity_id')].update(stat)
            for activity in self:
                activity.update(activity_data[activity._origin.id])

    @api.depends('activity_type', 'trace_ids')
    def _compute_statistics_graph_data(self):
        if not self.ids:
            date_range = [date.today() - timedelta(days=d) for d in range(0, 15)]
            date_range.reverse()
            default_values = [{'x': date_item.strftime('%d %b'), 'y': 0} for date_item in date_range]
            self.statistics_graph_data = json.dumps([
                {'points': default_values, 'label': _('Success'), 'color': '#28A745'},
                {'points': default_values, 'label': _('Rejected'), 'color': '#D23f3A'}])
        else:
            activity_data = {activity._origin.id: {} for activity in self}
            for act_id, graph_data in self._get_graph_statistics().items():
                activity_data[act_id]['statistics_graph_data'] = json.dumps(graph_data)
            for activity in self:
                activity.update(activity_data[activity._origin.id])

    def _get_activity_summary_dependencies(self):
        return ['activity_type', 'mass_mailing_id', 'server_action_id', 'interval_number', 'interval_type', 'trigger_type', 'parent_id', 'validity_duration', 'validity_duration_number', 'validity_duration_type']

    @api.depends(lambda self: self._get_activity_summary_dependencies())
    def _compute_activity_summary(self):
        """ Compute activity summary based on selection made by user, which includes information about the
        activity's starting point, the linked Server Action or Mail/SMS Template, trigger type, and the expiry duration.
        """
        for activity in self:
            activity.activity_summary = self.env['ir.qweb']._render('marketing_automation.marketing_activity_summary_template', {
                'activity': activity,
                'parent_activity_name': activity.parent_id.name,
                'activity_type_label': dict(activity._fields['activity_type']._description_selection(self.env))[activity.activity_type],
                'interval_type_label': dict(activity._fields['interval_type']._description_selection(self.env))[activity.interval_type],
                'validity_duration_type_label': dict(activity._fields['validity_duration_type']._description_selection(self.env))[activity.validity_duration_type]
            })

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if self._has_cycle():
            raise ValidationError(_("Error! You can't create recursive hierarchy of Activity."))

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            campaign_id = values.get('campaign_id')
            if not campaign_id:
                campaign_id = self.default_get(['campaign_id'])['campaign_id']
            values['require_sync'] = self.env['marketing.campaign'].browse(campaign_id).state == 'running'
        return super().create(vals_list)

    def copy_data(self, default=None):
        """ When copying the activities, we should also copy their mailings. """
        default = dict(default or {})
        if self.mass_mailing_id:
            default['mass_mailing_id'] = self.mass_mailing_id.copy().id
        return super(MarketingActivity, self).copy_data(default=default)

    def write(self, values):
        if any(activity.campaign_id.state == 'running' for activity in self) and any(field in values for field in ('interval_number', 'interval_type')):
            values['require_sync'] = True
        return super(MarketingActivity, self).write(values)

    def _get_full_statistics(self):
        self.env['marketing.trace'].flush_model(['activity_id', 'participant_id', 'state'])
        self.env['mailing.trace'].flush_model([
            'marketing_trace_id', 'links_click_datetime', 'sent_datetime', 'trace_status',
        ])
        self.env['marketing.participant'].flush_model(['is_test'])
        self.env.cr.execute("""
            SELECT
                trace.activity_id,
                COUNT(stat.sent_datetime) AS total_sent,
                COUNT(stat.links_click_datetime) AS total_click,
                COUNT(stat.trace_status) FILTER (WHERE stat.trace_status = 'reply') AS total_reply,
                COUNT(stat.trace_status) FILTER (WHERE stat.trace_status in ('open', 'reply')) AS total_open,
                COUNT(stat.trace_status) FILTER (WHERE stat.trace_status = 'bounce') AS total_bounce,
                COUNT(trace.state) FILTER (WHERE trace.state = 'processed') AS processed,
                COUNT(trace.state) FILTER (WHERE trace.state = 'rejected') AS rejected
            FROM
                marketing_trace AS trace
            LEFT JOIN
                mailing_trace AS stat
                ON (stat.marketing_trace_id = trace.id)
            JOIN
                marketing_participant AS part
                ON (trace.participant_id = part.id)
            WHERE
                (part.is_test = false or part.is_test IS NULL) AND
                trace.activity_id IN %s
            GROUP BY
                trace.activity_id;
        """, (tuple(self.ids), ))
        return self.env.cr.dictfetchall()

    def _get_graph_statistics(self):
        """ Compute activities statistics based on their traces state for the last fortnight """
        past_date = (self.env.cr.now() + timedelta(days=-14)).strftime('%Y-%m-%d 00:00:00')
        stat_map = {}
        base = date.today() + timedelta(days=-14)
        date_range = [base + timedelta(days=d) for d in range(0, 15)]

        self.env['marketing.trace'].flush_model(['activity_id', 'is_test', 'schedule_date', 'state'])
        self.env.cr.execute("""
            SELECT
                activity.id AS activity_id,
                trace.schedule_date::date AS dt,
                count(*) AS total,
                trace.state
            FROM
                marketing_trace AS trace
            JOIN
                marketing_activity AS activity
                ON (activity.id = trace.activity_id)
            WHERE
                activity.id IN %s AND
                trace.schedule_date >= %s AND
                (trace.is_test = false or trace.is_test IS NULL)
            GROUP BY activity.id , dt, trace.state
            ORDER BY dt;
        """, (tuple(self.ids), past_date))

        for stat in self.env.cr.dictfetchall():
            stat_map[(stat['activity_id'], stat['dt'], stat['state'])] = stat['total']
        graph_data = {}
        for activity in self:
            success = []
            rejected = []
            for i in date_range:
                x = i.strftime('%d %b')
                success.append({
                    'x': x,
                    'y': stat_map.get((activity._origin.id, i, 'processed'), 0)
                })
                rejected.append({
                    'x': x,
                    'y': stat_map.get((activity._origin.id, i, 'rejected'), 0)
                })
            graph_data[activity._origin.id] = [
                {'points': success, 'label': _('Success'), 'color': '#28A745'},
                {'points': rejected, 'label': _('Rejected'), 'color': '#D23f3A'}
            ]
        return graph_data

    def execute(self, domain=None):
        # auto-commit except in testing mode
        auto_commit = not getattr(threading.current_thread(), 'testing', False)

        # organize traces by activity
        trace_domain = [
            ('schedule_date', '<=', self.env.cr.now()),
            ('state', '=', 'scheduled'),
            ('activity_id', 'in', self.ids),
            ('participant_id.state', '=', 'running'),
        ]
        if domain:
            trace_domain += domain
        trace_to_activities = {
            activity: traces
            for activity, traces in self.env['marketing.trace']._read_group(
                trace_domain, groupby=['activity_id'], aggregates=['id:recordset']
            )
        }

        # execute activity on their traces
        BATCH_SIZE = 500  # same batch size as the MailComposer
        for activity, traces in trace_to_activities.items():
            for traces_batch in (traces[i:i + BATCH_SIZE] for i in range(0, len(traces), BATCH_SIZE)):
                activity.execute_on_traces(traces_batch)
                if auto_commit:
                    self.env.cr.commit()

    def execute_on_traces(self, traces):
        """ Execute current activity on given traces.

        :param traces: record set of traces on which the activity should run
        """
        self.ensure_one()
        now = self.env.cr.now()
        new_traces = self.env['marketing.trace']

        if self.validity_duration:
            duration = relativedelta(**{self.validity_duration_type: self.validity_duration_number})
            invalid_traces = traces.filtered(
                lambda trace: not trace.schedule_date or trace.schedule_date + duration < now
            )
            invalid_traces.action_cancel()
            traces = traces - invalid_traces

        # Filter traces not fitting the activity filter and whose record has been deleted
        if self.domain:
            rec_domain = literal_eval(self.domain)
        else:
            rec_domain = literal_eval(self.campaign_id.domain or '[]')
        if rec_domain:
            user_id = self.campaign_id.user_id or self.env.user
            rec_valid = self.env[self.model_name].with_context(lang=user_id.lang).search(rec_domain)
            rec_ids_domain = rec_valid.ids

            traces_allowed = traces.filtered(lambda trace: trace.res_id in rec_ids_domain)
            traces_rejected = traces.filtered(lambda trace: trace.res_id not in rec_ids_domain)  # either rejected, either deleted record
        else:
            traces_allowed = traces
            traces_rejected = self.env['marketing.trace']

        if traces_allowed:
            activity_method = getattr(self, '_execute_%s' % (self.activity_type))
            new_traces += self._generate_children_traces(traces_allowed)
            activity_method(traces_allowed)
            traces.mapped('participant_id').check_completed()

        if traces_rejected:
            traces_rejected.write({
                'state': 'rejected',
                'state_msg': _('Rejected by activity filter or record deleted / archived')
            })
            traces_rejected.mapped('participant_id').check_completed()

        return new_traces

    def _execute_action(self, traces):
        if not self.server_action_id:
            return False

        # Do a loop here because we have to try / catch each execution separately to ensure other traces are executed
        # and proper state message stored
        now = self.env.cr.now()
        traces_ok = self.env['marketing.trace']
        for trace in traces:
            action = self.server_action_id.with_context(
                active_model=self.model_name,
                active_ids=[trace.res_id],
                active_id=trace.res_id,
            )
            try:
                action.run()
            except Exception as e:
                _logger.warning('Marketing Automation: activity <%s> encountered server action issue %s', self.id, str(e), exc_info=True)
                trace.write({
                    'state': 'error',
                    'schedule_date': now,
                    'state_msg': _('Exception in server action: %s', e),
                })
            else:
                traces_ok += trace

        # Update status
        traces_ok.write({
            'state': 'processed',
            'schedule_date': self.env.cr.now(),
        })
        return True

    def _execute_email(self, traces):
        # we only allow to continue if the user has sufficient rights, as a sudo() follows
        if not self.env.is_superuser() and not self.env.user.has_group('marketing_automation.group_marketing_automation_user'):
            raise AccessError(_('To use this feature you should be an administrator or belong to the marketing automation group.'))

        def _uniquify_list(seq):
            seen = set()
            return [x for x in seq if x not in seen and not seen.add(x)]
        res_ids = _uniquify_list(traces.mapped('res_id'))
        ctx = dict(clean_context(self._context), default_marketing_activity_id=self.ids[0], active_ids=res_ids)
        mailing = self.mass_mailing_id.sudo().with_context(ctx)
        now = self.env.cr.now()

        try:
            mailing.action_send_mail(res_ids)
        except Exception as e:
            _logger.warning('Marketing Automation: activity <%s> encountered mass mailing issue %s', self.id, str(e), exc_info=True)
            traces.write({
                'state': 'error',
                'schedule_date': now,
                'state_msg': _('Exception in mass mailing: %s', e),
            })
        else:
            # TDE Note: bounce is not really set at launch, let us consider it as an error
            failed_stats = self.env['mailing.trace'].sudo().search([
                ('marketing_trace_id', 'in', traces.ids),
                ('trace_status', 'in', ['error', 'bounce', 'cancel'])
            ])
            error_doc_ids = [stat.res_id for stat in failed_stats if stat.trace_status in ('error', 'bounce')]
            cancel_doc_ids = [stat.res_id for stat in failed_stats if stat.trace_status == 'cancel']

            processed_traces = traces
            canceled_traces = traces.filtered(lambda trace: trace.res_id in cancel_doc_ids)
            error_traces = traces.filtered(lambda trace: trace.res_id in error_doc_ids)

            if canceled_traces:
                canceled_traces.write({
                    'state': 'canceled',
                    'schedule_date': now,
                    'state_msg': _('Email cancelled')
                })
                processed_traces = processed_traces - canceled_traces
            if error_traces:
                error_traces.write({
                    'state': 'error',
                    'schedule_date': now,
                    'state_msg': _('Email failed')
                })
                processed_traces = processed_traces - error_traces
            if processed_traces:
                processed_traces.write({
                    'state': 'processed',
                    'schedule_date': now,
                })
        return True

    def _generate_children_traces(self, traces):
        """Generate child traces for child activities that are directly time
        dependant e.g. after an activity, after not opened email, ...
        Action-based traces (mail open, ...) have no specific scheduled date
        as they depend on external actions.

        :param traces: marketing.trace records which have been processed and
          validated and for which we want to generate children traces
        """
        child_traces = self.env['marketing.trace']
        cron_trigger_dates = set()
        for activity in self.child_ids:
            activity_offset = relativedelta(**{activity.interval_type: activity.interval_number})

            for trace in traces:
                vals = {
                    'parent_id': trace.id,
                    'participant_id': trace.participant_id.id,
                    'activity_id': activity.id
                }
                if activity.trigger_type in self._get_reschedule_trigger_types():
                    schedule_date = Datetime.from_string(trace.schedule_date) + activity_offset
                    vals['schedule_date'] = schedule_date
                    cron_trigger_dates.add(schedule_date)
                child_traces += child_traces.create(vals)

        if cron_trigger_dates:
            # based on created activities, we schedule CRON triggers that match the scheduled_dates
            # we use a set to only trigger the CRON once per timeslot event if there are multiple
            # marketing.participants
            cron = self.env.ref('marketing_automation.ir_cron_campaign_execute_activities')
            cron._trigger(cron_trigger_dates)

        return child_traces

    def _get_reschedule_trigger_types(self):
        """ Retrieve a set of trigger types that have a schedule_date that depends
        on parent or activity / campaign, not on external user actions.

        :returns set[str]: set of ``trigger_type`` elements
        """
        return {'activity', 'begin', 'mail_not_open', 'mail_not_click', 'mail_not_reply'}

    def action_view_sent(self):
        return self._action_view_documents_filtered('sent')

    def action_view_replied(self):
        return self._action_view_documents_filtered('reply')

    def action_view_clicked(self):
        return self._action_view_documents_filtered('click')

    def action_view_opened(self):
        return self._action_view_documents_filtered('open')

    def _action_view_documents_filtered(self, view_filter):
        if not self.mass_mailing_id:  # Only available for mass mailing
            return False
        action = self.env["ir.actions.actions"]._for_xml_id("marketing_automation.marketing_participants_action_mail")

        if view_filter == 'reply':
            found_traces = self.trace_ids.filtered(lambda trace: trace.mailing_trace_status == view_filter)
        elif view_filter == 'open':
            found_traces = self.trace_ids.filtered(lambda trace: trace.mailing_trace_status in ('open', 'reply'))
        elif view_filter == 'sent':
            found_traces = self.trace_ids.filtered('mailing_trace_ids.sent_datetime')
        elif view_filter == 'click':
            found_traces = self.trace_ids.filtered('mailing_trace_ids.links_click_datetime')
        else:
            found_traces = self.env['marketing.trace']

        participants = found_traces.participant_id
        action.update({
            'display_name': _('Participants of %(activity)s (%(filter)s)', activity=self.name, filter=view_filter),
            'domain': [('id', 'in', participants.ids)],
            'context': dict(self._context, create=False)
        })
        return action
