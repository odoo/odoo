# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.misc import str2bool


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    pending_email_template_id = fields.Many2one(
        string="Pending Email Template",
        help="The template of the pending email that must be sent asynchronously.",
        comodel_name='mail.template',
        ondelete='set null',
        readonly=True,
    )

    def _send_order_notification_mail(self, mail_template):
        """ Override of `sale` to reschedule order status emails to be sent asynchronously. """
        async_send = str2bool(self.env['ir.config_parameter'].sudo().get_param('sale.async_emails'))
        cron = async_send and self.env.ref('sale_async_emails.cron', raise_if_not_found=False)
        if async_send and cron and not self.env.context.get('is_async_email', False):
            # Schedule the email to be sent asynchronously.
            self.pending_email_template_id = mail_template
            cron._trigger()
        else:  # We are in the cron job, or the user has disabled async emails.
            super()._send_order_notification_mail(mail_template)  # Send the email synchronously.

    @api.model
    def _cron_send_pending_emails(self, auto_commit=True):
        """ Find and send pending order status emails asynchronously.

        :param bool auto_commit: Whether the database cursor should be committed as soon as an email
                                 is sent. Set to False in unit tests.
        :return: None
        """
        pending_email_orders = self.search([('pending_email_template_id', '!=', False)])
        for order in pending_email_orders:
            order = order[0]  # Avoid pre-fetching after each cache invalidation due to committing.
            order.with_context(is_async_email=True)._send_order_notification_mail(
                order.pending_email_template_id
            )  # Asynchronously resume the email sending.
            order.pending_email_template_id = None
            if auto_commit:
                self.env.cr.commit()  # Save progress in case the cron is killed.
