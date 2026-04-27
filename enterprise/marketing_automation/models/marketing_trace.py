# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class MarketingTrace(models.Model):
    _name = 'marketing.trace'
    _description = 'Marketing Trace'
    _order = 'schedule_date DESC, id ASC'
    _rec_name = 'participant_id'

    participant_id = fields.Many2one(
        'marketing.participant', string='Participant',
        index=True, ondelete='cascade', required=True)
    res_id = fields.Integer(string='Document ID', related='participant_id.res_id', index=True, store=True, readonly=False)
    is_test = fields.Boolean(string='Test Trace', related='participant_id.is_test', index=True, store=True, readonly=True)
    activity_id = fields.Many2one(
        'marketing.activity', string='Activity',
        index=True, ondelete='cascade', required=True)
    activity_type = fields.Selection(related='activity_id.activity_type', readonly=True)
    trigger_type = fields.Selection(related='activity_id.trigger_type', readonly=True)

    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('processed', 'Processed'),
        ('rejected', 'Rejected'),
        ('canceled', 'Cancelled'),
        ('error', 'Error')
        ], default='scheduled', index=True, required=True)
    schedule_date = fields.Datetime()
    state_msg = fields.Char(string='Error message')
    # hierarchy
    parent_id = fields.Many2one('marketing.trace', string='Parent', index=True, ondelete='cascade')
    child_ids = fields.One2many('marketing.trace', 'parent_id', string='Direct child traces')
    # mailing traces
    mailing_trace_ids = fields.One2many('mailing.trace', 'marketing_trace_id', string='Mass mailing statistics')
    mailing_trace_status = fields.Selection(related='mailing_trace_ids.trace_status', readonly=True)
    links_click_datetime = fields.Datetime(compute='_compute_links_click_datetime')

    @api.depends('mailing_trace_ids')
    def _compute_links_click_datetime(self):
        # necessary, because sometimes mailing_trace_ids aren't available
        # due to failed messages, which prevents `links_click_datetime` to get assigned
        self.links_click_datetime = False
        mailing_trace = self.filtered(lambda x: x.mailing_trace_ids)
        for trace in mailing_trace:
            trace.links_click_datetime = trace.mailing_trace_ids[0].links_click_datetime

    def participant_action_cancel(self):
        self.action_cancel(message=_('Manually'))

    def action_cancel(self, message=None):
        values = {'state': 'canceled', 'schedule_date': self.env.cr.now()}
        if message:
            values['state_msg'] = message
        self.write(values)
        self.mapped('participant_id').check_completed()

    def action_execute(self):
        self.activity_id.execute_on_traces(self)

    # DANE: try to make this function to work on batches later
    def process_event(self, action):
        """ Process event coming from customers. It updates child traces :

         * child trace matching action is scheduled or executed depending on
           time interval configuration;
         * opposite actions are canceled
           e.g. mail_not_open is canceled if mail_open is triggered
           e.g. mail_bounce cancels all child actions not being mail_bounced;

        :param string action: one of ``trigger_type`` of marketing activity
        """
        self.ensure_one()
        if self.participant_id.campaign_id.state not in ['draft', 'running']:
            return

        now = self.env.cr.now()
        msg = {
            'mail_not_reply': _('Parent activity mail replied'),
            'mail_not_click': _('Parent activity mail clicked'),
            'mail_not_open': _('Parent activity mail opened'),
            'mail_bounce': _('Parent activity mail bounced'),
        }

        opened_child = self.child_ids.filtered(lambda trace: trace.state == 'scheduled')

        cron_trigger_dates = set()
        for next_trace in opened_child.filtered(lambda trace: trace.activity_id.trigger_type == action):
            if next_trace.activity_id.interval_number == 0:
                next_trace.write({
                    'schedule_date': now,
                })
                next_trace.activity_id.execute_on_traces(next_trace)
            else:
                schedule_date = now + relativedelta(**{
                    next_trace.activity_id.interval_type: next_trace.activity_id.interval_number
                })
                next_trace.write({
                    'schedule_date': schedule_date,
                })
                cron_trigger_dates.add(schedule_date)

        if cron_trigger_dates:
            # based on updated activities, we schedule CRON triggers that match the scheduled_dates
            # we use a set to only trigger the CRON once per timeslot event if there are multiple
            # marketing.participants
            cron = self.env.ref('marketing_automation.ir_cron_campaign_execute_activities')
            cron._trigger(cron_trigger_dates)

        if action in ['mail_reply', 'mail_click', 'mail_open']:
            opposite_trigger = action.replace('_', '_not_')
            opened_child.filtered(
                lambda trace: trace.activity_id.trigger_type == opposite_trigger
            ).action_cancel(message=msg[opposite_trigger])

        elif action == 'mail_bounce':
            opened_child.filtered(
                lambda trace: trace.activity_id.trigger_type != 'mail_bounce'
            ).action_cancel(message=msg[action])

        return True

    def _update_schedule_date(self):
        """ Update scheduled date of traces, based on activity interval fields
        update. Rationale

          * begin activities: offset is based on participant creation e.g.
            2 days after entering the campaign;
          * reschedule triggers: based on parent trace scheduled date e.g.
            mail_not_open triggered 2 days after sending the mailing aka the
            parent activity;
          * other triggers: reschedule only if already scheduled, based on a
            master record e.g. 2 days after opening an email is based on the
            mailing trace;
        """
        reschedule_types = self.env["marketing.activity"]._get_reschedule_trigger_types()
        for trace in self:
            base_dt_str = False
            trace_offset = relativedelta(**{trace.activity_id.interval_type: trace.activity_id.interval_number})
            # begin: based on participant creation as it is their first one
            if trace.activity_id.trigger_type == 'begin':
                base_dt_str = trace.participant_id.create_date
            # reschedule (mail_not_open, ...) -> based on parent
            elif trace.trigger_type in reschedule_types:
                base_dt_str = trace.parent_id.schedule_date or trace.parent_id.mailing_trace_ids[0].write_date or trace.participant_id.create_date
            # other (mail_open, ...): update only already scheduled traces, other unscheduled should stay as it
            elif trace.schedule_date and trace.parent_id.mailing_trace_ids:
                base_dt_str = trace.parent_id.mailing_trace_ids[0].write_date

            if base_dt_str:
                trace.schedule_date = fields.Datetime.from_string(base_dt_str) + trace_offset
