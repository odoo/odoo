# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields, models, _
from odoo.fields import Datetime


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
        ('canceled', 'Canceled'),
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
    links_click_datetime = fields.Datetime(related='mailing_trace_ids.links_click_datetime', readonly=True)

    def participant_action_cancel(self):
        self.action_cancel(message=_('Manually'))

    def action_cancel(self, message=None):
        values = {'state': 'canceled', 'schedule_date': Datetime.now()}
        if message:
            values['state_msg'] = message
        self.write(values)
        self.mapped('participant_id').check_completed()

    def action_execute(self):
        self.activity_id.execute_on_traces(self)

    def process_event(self, action):
        """Process event coming from customers currently centered on email actions.
        It updates child traces :

         * opposite actions are canceled, for example mail_not_open when mail_open is triggered;
         * bounced mail cancel all child actions not being mail_bounced;

        :param string action: see trigger_type field of activity
        """
        self.ensure_one()
        if self.participant_id.campaign_id.state not in ['draft', 'running']:
            return

        now = Datetime.from_string(Datetime.now())
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
