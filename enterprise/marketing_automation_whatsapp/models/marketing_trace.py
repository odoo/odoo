from odoo import api, fields, models, _


class MarketingTrace(models.Model):
    _inherit = 'marketing.trace'

    whatsapp_message_id = fields.Many2one(
        'whatsapp.message', string='Marketing Template',
        index='btree_not_null', readonly=False)

    @api.depends('whatsapp_message_id')
    def _compute_links_click_datetime(self):
        wa_trace = self.filtered(lambda x: x.whatsapp_message_id)
        wa_trace.links_click_datetime = False
        super(MarketingTrace, self - wa_trace)._compute_links_click_datetime()
        for trace in wa_trace:
            trace.links_click_datetime = trace.whatsapp_message_id.links_click_datetime

    def process_event(self, action):
        self.ensure_one()
        res = super().process_event(action)
        if not res:
            return res
        opened_child = self.child_ids.filtered(lambda trace: trace.state == 'scheduled')
        if action == 'whatsapp_read':
            opened_child.filtered(
                lambda trace: trace.activity_id.trigger_type == 'whatsapp_not_read'
            ).action_cancel(message=_('Parent Whatsapp message got opened'))
        elif action == 'whatsapp_replied':
            opened_child.filtered(
                lambda trace: trace.activity_id.trigger_type == 'whatsapp_not_replied'
            ).action_cancel(message=_('Parent Whatsapp was replied to'))
        elif action == 'whatsapp_click':
            opened_child.filtered(
                lambda trace: trace.activity_id.trigger_type == 'whatsapp_not_click'
            ).action_cancel(message=_('Parent Whatsapp message was clicked'))
        elif action == 'whatsapp_bounced':
            opened_child.filtered(
                lambda trace: trace.activity_id.trigger_type != 'whatsapp_bounced'
            ).action_cancel(message=_('Parent whatsapp was bounced'))
        return res
