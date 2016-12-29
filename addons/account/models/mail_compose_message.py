# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        context = self._context
        if context.get('default_model') == 'account.invoice' and \
                context.get('default_res_id') and context.get('mark_invoice_as_sent'):
            invoice = self.env['account.invoice'].browse(context['default_res_id'])
            invoice = invoice.with_context(mail_post_autofollow=True)
            invoice.message_post(body=_("Invoice sent"))
        return super(MailComposeMessage, self).send_mail(auto_commit=auto_commit)

    @api.multi
    @api.onchange('template_id')
    def onchange_template_id_wrapper(self):
        super(MailComposeMessage, self).onchange_template_id_wrapper()
        # Append edi documents if necessary
        if self.env.user.company_id.edi_xml_attached_mails:
            invoice = self.env[self.model].browse(self.res_id)
            l = lambda x: x.id
            ids = map(l, self.attachment_ids)
            ids.extend(map(l, invoice._get_edi_attachments()))
            self.attachment_ids = [(6, 0, ids)]