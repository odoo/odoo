import logging

from odoo import api, fields, models, _
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


class MarketingActivity(models.Model):
    _inherit = 'marketing.activity'

    activity_type = fields.Selection(selection_add=[
        ('whatsapp', 'Whatsapp Message')
    ], ondelete={'whatsapp': 'cascade'})

    whatsapp_template_id = fields.Many2one(
        "whatsapp.template",
        string="Whatsapp Template",
        compute="_compute_whatsapp_template_id",
        readonly=False,
        ondelete="restrict",
        store=True,
    )

    trigger_type = fields.Selection(selection_add=[
        ('whatsapp_click', 'Whatsapp: click'),
        ('whatsapp_not_click', 'Whatsapp: not click'),
        ('whatsapp_read', 'Whatsapp: opened'),
        ('whatsapp_not_read', 'Whatsapp: not opened'),
        ('whatsapp_replied', 'Whatsapp: replied'),
        ('whatsapp_not_replied', 'Whatsapp: not replied'),
        ('whatsapp_bounced', 'Whatsapp: message bounced'),
    ], ondelete={
        'whatsapp_click': 'cascade',
        'whatsapp_not_click': 'cascade',
        'whatsapp_read': 'cascade',
        'whatsapp_not_read': 'cascade',
        'whatsapp_replied': 'cascade',
        'whatsapp_not_replied': 'cascade',
        'whatsapp_bounced': 'cascade',
    })
    trigger_category = fields.Selection(selection_add=[('whatsapp', 'WhatsApp')], compute='_compute_trigger_category')
    whatsapp_error = fields.Boolean('Whatsapp Error', compute="_compute_whatsapp_error", store=True)

    @api.depends('activity_type')
    def _compute_mass_mailing_id(self):
        whatsapp_activities = self.filtered(lambda activity: activity.activity_type == 'whatsapp')
        whatsapp_activities.mass_mailing_id = False
        super(MarketingActivity, self - whatsapp_activities)._compute_mass_mailing_id()

    @api.depends('trigger_type')
    def _compute_trigger_category(self):
        whatsapp_types = ['whatsapp_click', 'whatsapp_not_click',
                          'whatsapp_read', 'whatsapp_not_read', 'whatsapp_replied',
                          'whatsapp_not_replied', 'whatsapp_bounced', 'message_cancel']
        whatsapp_activities = self.filtered(lambda activity: activity.trigger_type in whatsapp_types)
        whatsapp_activities.trigger_category = 'whatsapp'
        super(MarketingActivity, self - whatsapp_activities)._compute_trigger_category()

    @api.onchange('whatsapp_template_id')
    def _compute_whatsapp_error(self):
        failing = self.filtered(
            lambda a: a.whatsapp_template_id and any(btn.url_type != 'tracked' for btn in a.whatsapp_template_id.button_ids)
        )
        (self - failing).whatsapp_error = False
        failing.whatsapp_error = True

    @api.depends('activity_type')
    def _compute_whatsapp_template_id(self):
        non_whatsapp_activities = self.filtered(lambda activity: activity.activity_type != 'whatsapp')
        non_whatsapp_activities.whatsapp_template_id = False

    def _get_activity_summary_dependencies(self):
        summary_dependency = super()._get_activity_summary_dependencies()
        summary_dependency.append('whatsapp_template_id')
        return summary_dependency

    def _get_full_statistics(self):
        whatsapp_activities = self.filtered(lambda activity: activity.activity_type == 'whatsapp')
        non_whatsapp_activities = self - whatsapp_activities

        non_whatsapp_stats = (
            super(MarketingActivity, non_whatsapp_activities)._get_full_statistics()
            if non_whatsapp_activities else []
        )

        if not whatsapp_activities:
            return non_whatsapp_stats

        self.env["marketing.trace"].flush_model(["activity_id", "whatsapp_message_id", "participant_id"])
        self.env["whatsapp.message"].flush_model(["state", "links_click_datetime"])
        self.env.cr.execute(SQL("""
            SELECT
                trace.activity_id,
                COUNT(wa_message.state) FILTER (WHERE wa_message.state in ('sent', 'delivered', 'read', 'replied')) AS total_sent,
                COUNT(wa_message.state) FILTER (WHERE wa_message.state in ('read', 'replied')) AS total_open,
                COUNT(wa_message.state) FILTER (WHERE wa_message.state in ('replied')) AS total_reply,
                COUNT(wa_message.state) FILTER (WHERE wa_message.state in ('error')) AS rejected,
                COUNT(wa_message.state) FILTER (WHERE wa_message.links_click_datetime is NOT NULL) AS total_click
            FROM
                marketing_trace AS trace
            LEFT JOIN
                whatsapp_message AS wa_message
            ON (wa_message.id = trace.whatsapp_message_id)
            JOIN
                marketing_participant AS part
            ON (trace.participant_id = part.id)
            WHERE
                (part.is_test = false or part.is_test IS NULL) AND
                trace.activity_id IN %s
            GROUP BY
            trace.activity_id;
        """, tuple(whatsapp_activities.ids)))

        return non_whatsapp_stats + self.env.cr.dictfetchall()

    def _get_reschedule_trigger_types(self):
        types = super()._get_reschedule_trigger_types()
        types |= {'whatsapp_not_read', 'whatsapp_not_replied', 'whatsapp_not_click'}
        return types

    def _execute_whatsapp(self, traces):
        res_ids = [res_id for res_id in set(traces.mapped('res_id')) if res_id]
        now = self.env.cr.now()

        composer_vals = {
            'res_model': self.model_name, 'res_ids': res_ids,
            'wa_template_id': self.whatsapp_template_id.id,
            'batch_mode': True,
        }
        try:
            composer = self.env['whatsapp.composer'].with_context(active_model=self.model_name).create(composer_vals)
            messages = composer._create_whatsapp_messages(force_create=True)
            message_by_res_id = {r.mail_message_id.res_id: r for r in messages}
            for trace in self.trace_ids:
                res_id = trace.res_id
                message = message_by_res_id.get(res_id, self.env['whatsapp.message'])
                if message:
                    trace.whatsapp_message_id = message.id
                if not message.mobile_number:
                    message.state = 'error'
                    message.failure_type = 'phone_invalid'

            # at most 500 messages are sent at one go, so there is no reason to divide them further.
            messages._send()

        except Exception as e:  # noqa: BLE001 we don't want to crash because if error occurs during sending, we should assign traces 'error' state
            _logger.warning('Marketing Automation: activity <%s> encountered WhatsApp message issue %s', self.id, str(e))
            traces.write({
                'state': 'error',
                'schedule_date': now,
                'state_msg': _('Exception in Whatsapp Marketing: %s', e),
            })
        else:
            cancelled_traces = traces.filtered(lambda trace: trace.whatsapp_message_id.state == 'cancel')
            error_traces = traces.filtered(lambda trace: trace.whatsapp_message_id.state == 'error')

            if cancelled_traces:
                cancelled_traces.write({
                    'state': 'canceled',
                    'schedule_date': now,
                    'state_msg': _('WhatsApp canceled')
                })
            if error_traces:
                error_traces.write({
                    'state': 'error',
                    'schedule_date': now,
                    'state_msg': _('WhatsApp failed')
                })
            processed_traces = traces - (cancelled_traces | error_traces)
            if processed_traces:
                processed_traces.write({
                    'state': 'processed',
                    'schedule_date': now,
                })
        return True

    def action_view_sent_wa(self):
        return self._action_view_documents_filtered_wa('sent')

    def action_view_delivered_wa(self):
        return self._action_view_documents_filtered_wa('delivered')

    def action_view_read_wa(self):
        return self._action_view_documents_filtered_wa('read')

    def action_view_clicked_wa(self):
        return self._action_view_documents_filtered_wa('clicked')

    def action_view_replied_wa(self):
        return self._action_view_documents_filtered_wa('replied')

    def _action_view_documents_filtered_wa(self, view_filter):
        """Return an action with a domain tailored to the `view_filter` parameter.

        The domain dynamically includes WhatsApp message states based on `view_filter` values:
        - 'sent', 'delivered', 'read', 'replied': The filter builds on state progressions, where 'delivered' includes 'sent', etc.
        - 'clicked': Filters for messages with clicked links.
        Other values default to all traces.

        :param view_filter:  A filter condition ('sent', 'delivered', 'read', 'replied', 'clicked', etc.).
        :return: Updated action dictionary with domain and context set according to the filter.
        """
        action = self.env["ir.actions.actions"]._for_xml_id("marketing_automation.marketing_participants_action_mail")
        orders = ['sent', 'delivered', 'read', 'replied']
        if view_filter in orders:
            idx = orders.index(view_filter)
            found_traces = self.trace_ids.filtered(lambda trace: trace.whatsapp_message_id.state in orders[idx:])
        elif view_filter == 'clicked':
            found_traces = self.trace_ids.filtered(lambda trace: trace.whatsapp_message_id.links_click_datetime)
        else:
            found_traces = self.env['marketing.trace']

        action.update({
            'display_name': _('Participants of %(name)s (%(filter)s)', name=self.name, filter=view_filter),
            'domain': [('id', 'in', found_traces.participant_id.ids)],
            'context': dict(self.env.context, create=False)
        })
        return action
