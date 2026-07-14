# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    def action_schedule_message(self, scheduled_date=False):
        return super(
            MailComposer,
            self.with_context(schedule_mark_so_as_sent=self.env.context.get('mark_so_as_sent')),
        ).action_schedule_message(scheduled_date=scheduled_date)

    def _prepare_mail_values_rendered(self, res_ids):
        values = super()._prepare_mail_values_rendered(res_ids)
        if self.model == 'sale.order' and self.env.context.get('schedule_mark_so_as_sent'):
            for res_id in res_ids:
                values[res_id]['mark_so_as_sent'] = True
        return values
