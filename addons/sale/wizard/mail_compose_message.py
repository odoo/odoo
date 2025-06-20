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

    def _compute_authorship(self):
        super()._compute_authorship()
        # mail's author lookup can mix up partners with identical email addresses,
        # this override ensures the author is set to the partner responsible for the sale order
        for composer in self.filtered(lambda c: c.model == 'sale.order'):
            res_ids = composer._evaluate_res_ids()
            if len(res_ids) != 1:
                continue
            order_sudo = self.env['sale.order'].sudo().browse(res_ids)
            author_sudo = (order_sudo.user_id or order_sudo.company_id).partner_id
            if (
                author_sudo != composer.author_id
                and author_sudo.email == composer.author_id.email
            ):
                composer.update({
                    'author_id': author_sudo.id,
                    'email_from': author_sudo.email_formatted,
                })
