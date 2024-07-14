# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _
from odoo.fields import Datetime
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class MarketingActivity(models.Model):
    _inherit = ['marketing.activity']

    activity_type = fields.Selection(selection_add=[
        ('sms', 'SMS')
    ], ondelete={'sms': 'cascade'})
    mass_mailing_id_mailing_type = fields.Selection(selection_add=[('sms', 'SMS')])
    trigger_type = fields.Selection(selection_add=[
        ('sms_click', 'SMS: clicked'),
        ('sms_not_click', 'SMS: not clicked'),
        ('sms_bounce', 'SMS: bounced')
    ], ondelete={
        'sms_click': 'cascade',
        'sms_not_click': 'cascade',
        'sms_bounce': 'cascade',
    })
    trigger_category = fields.Selection(selection_add=[('sms', 'SMS')], compute='_compute_trigger_category')

    @api.depends('activity_type')
    def _compute_mass_mailing_id_mailing_type(self):
        for activity in self:
            if activity.activity_type == 'sms':
                activity.mass_mailing_id_mailing_type = 'sms'
        super(MarketingActivity, self)._compute_mass_mailing_id_mailing_type()

    @api.depends('trigger_type')
    def _compute_trigger_category(self):
        non_sms_trigger_category = self.env['marketing.activity']
        for activity in self:
            if activity.trigger_type in ['sms_click', 'sms_not_click', 'sms_bounce']:
                activity.trigger_category = 'sms'
            else:
                non_sms_trigger_category |= activity

        super(MarketingActivity, non_sms_trigger_category)._compute_trigger_category()

    def _get_reschedule_trigger_types(self):
        trigger_types = super()._get_reschedule_trigger_types()
        trigger_types.add('sms_not_click')
        return trigger_types

    def _execute_sms(self, traces):
        res_ids = [r for r in set(traces.mapped('res_id'))]

        # we only allow to continue if the user has sufficient rights, as a sudo() follows
        if not self.env.is_superuser() and not self.user_has_groups('marketing_automation.group_marketing_automation_user'):
            raise AccessError(_('To use this feature you should be an administrator or belong to the marketing automation group.'))

        mailing = self.mass_mailing_id.sudo().with_context(default_marketing_activity_id=self.ids[0])
        try:
            mailing.action_send_sms(res_ids)
        except Exception as e:
            _logger.warning('Marketing Automation: activity <%s> encountered mass mailing issue %s', self.id, str(e), exc_info=True)
            traces.write({
                'state': 'error',
                'schedule_date': Datetime.now(),
                'state_msg': _('Exception in SMS Marketing: %s', e),
            })
        else:
            failed_stats = self.env['mailing.trace'].sudo().search([
                ('marketing_trace_id', 'in', traces.ids),
                ('trace_status', 'in', ['error', 'cancel'])
            ])
            cancel_doc_ids = [stat.res_id for stat in failed_stats if stat.trace_status == 'cancel']
            error_doc_ids = [stat.res_id for stat in failed_stats if stat.trace_status == 'error']

            processed_traces = traces
            canceled_traces = traces.filtered(lambda trace: trace.res_id in cancel_doc_ids)
            error_traces = traces.filtered(lambda trace: trace.res_id in error_doc_ids)

            if canceled_traces:
                canceled_traces.write({
                    'state': 'canceled',
                    'schedule_date': Datetime.now(),
                    'state_msg': _('SMS canceled')
                })
                processed_traces = processed_traces - canceled_traces
            if error_traces:
                error_traces.write({
                    'state': 'error',
                    'schedule_date': Datetime.now(),
                    'state_msg': _('SMS failed')
                })
                processed_traces = processed_traces - error_traces
            if processed_traces:
                processed_traces.write({
                    'state': 'processed',
                    'schedule_date': Datetime.now(),
                })
        return True
