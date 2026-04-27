from odoo import models


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    def message_post(self, *, message_type='notification', **kwargs):
        """
        Overrides the base message_post to handle specific cases for WhatsApp messages
        that are responses to existing messages. The responses can happen two ways:
        1) swipe right, 2) direct response. for the first case parent message is available
        which makes it easier to detect for which the message was replied to, for the second
        case we assume that message was replied towards all previously sent templates.
        """
        new_msg = super().message_post(message_type=message_type, **kwargs)
        if message_type != 'whatsapp_message':
            return new_msg

        received_message = new_msg.sudo().wa_message_ids
        if not received_message:
            return new_msg

        parent_wa_msg = received_message.parent_id
        if not parent_wa_msg:
            parent_wa_msg = self.env['whatsapp.message'].sudo().search(
                [
                    ('wa_template_id', '!=', None),
                    ('marketing_trace_ids', '!=', False),
                    ('mobile_number_formatted', '=', received_message.mobile_number_formatted),
                    ('state', 'not in', ['error', 'replied']),
                ],
                order='id DESC', limit=1,
            )
        for parent_trace in parent_wa_msg.marketing_trace_ids:
            parent_trace.process_event('whatsapp_replied')
        parent_wa_msg.state = 'replied'
        return new_msg
