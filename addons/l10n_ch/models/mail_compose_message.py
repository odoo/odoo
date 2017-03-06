# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        """ Method overriden to mark ISR as sent once a mail containing
        it in attachment has been sent.
        """
        context = self._context
        if context.get('default_model') == 'account.invoice' and \
                context.get('default_res_id') and \
                context.get('l10n_ch_mark_isr_as_sent', False):

            invoice = self.env['account.invoice'].browse(context['default_res_id'])
            invoice = invoice.with_context(mail_post_autofollow=True)
            invoice.l10n_ch_isr_sent = True
            invoice.message_post(body=_("ISR sent"))

        return super(MailComposer, self).send_mail(auto_commit=auto_commit)