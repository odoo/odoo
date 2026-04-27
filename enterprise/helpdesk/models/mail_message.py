# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model_create_multi
    def create(self, values_list):
        messages = super().create(values_list)
        # We measure the time between the customer's message
        # or ticket's create date, and the helpdesk response of subtype comment (not note).
        # If several messages are sent before any response,
        # in both directions, we take the first one.

        # EVENT  | CUSTOMER  | HELPDESK  | MEASURED
        # create |     x     |           |     ↑
        # msg    |     x     |           |     |
        # note   |           |     x     |     |
        # msg    |           |     x     |     ↓
        # msg    |           |     x     |
        # note   |     x     |           |
        # msg    |     x     |           |     ↑
        # msg    |           |     x     |     ↓
        # ...
        if not any(values.get('model') == 'helpdesk.ticket' for values in values_list):
            return messages

        comment_subtype = self.env.ref('mail.mt_comment')
        filtered_messages = messages.filtered(
            lambda m: m.model == 'helpdesk.ticket' and m.subtype_id == comment_subtype
        )
        if not filtered_messages:
            return messages

        tickets = self.env['helpdesk.ticket'].sudo().search(
            [('close_date', '=', False), ('id', 'in', filtered_messages.mapped('res_id'))]
        )
        ticket_per_id = {t.id: t for t in tickets}
        if not tickets:
            return messages

        for message in filtered_messages.sorted(lambda m: m.date):
            ticket = ticket_per_id.get(message.res_id)
            if not ticket:
                continue
            oldest_unanswered_customer_message_date = ticket.oldest_unanswered_customer_message_date
            is_helpdesk_msg = any(not user.share for user in message.author_id.user_ids)

            if not oldest_unanswered_customer_message_date and not is_helpdesk_msg:
                # customer initiated an exchange
                ticket.oldest_unanswered_customer_message_date = message.date

            elif oldest_unanswered_customer_message_date and is_helpdesk_msg:
                # internal user responded to the customer
                ticket.oldest_unanswered_customer_message_date = False
                calendar = ticket.team_id.resource_calendar_id or self.env.company.resource_calendar_id
                if not calendar:
                    continue

                duration_data = calendar.get_work_duration_data(oldest_unanswered_customer_message_date, message.date, compute_leaves=True)
                delta_hours = duration_data['hours']
                if not ticket.answered_customer_message_count:
                    ticket.first_response_hours = delta_hours
                ticket.answered_customer_message_count += 1
                ticket.total_response_hours += delta_hours
                ticket.avg_response_hours = ticket.total_response_hours / ticket.answered_customer_message_count
            else:
                # a new message is received, `write_date` should be updated
                ticket.write({})

        return messages
