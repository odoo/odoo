# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _action_send_mail(self, auto_commit=False):
        composers = self
        if not self.env.context.get('mark_so_as_sent'):
            quotation_tmpl = self.env.ref('sale.email_template_edi_sale', raise_if_not_found=False)
            if quotation_tmpl and self and all(
                wizard.model == 'sale.order' and wizard.template_id == quotation_tmpl
                for wizard in self
            ):
                composers = self.with_context(mark_so_as_sent=True)
        return super(MailComposer, composers)._action_send_mail(auto_commit=auto_commit)

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
