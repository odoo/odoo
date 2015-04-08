# -*- coding: utf-8 -*-

from openerp import api, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def invoice_validate_send_email(self):
        Composer = self.env['mail.compose.message']
        for invoice in self:
            # send template only on customer invoice
            if invoice.type != 'out_invoice':
                continue
            # subscribe the partner to the invoice
            if invoice.partner_id not in invoice.message_follower_ids:
                invoice.message_subscribe([invoice.partner_id.id])
            for line in invoice.invoice_line:
                if line.product_id.email_template_id:
                    # CLEANME: should define and use a clean API: message_post with a template
                    composer = Composer.create({
                        'model': 'account.invoice',
                        'res_id': invoice.id,
                        'template_id': line.product_id.email_template_id.id,
                        'composition_mode': 'comment'})
                    template_values = composer.onchange_template_id(line.product_id.email_template_id.id, 'comment', 'account.invoice', invoice.id)['value']
                    template_values['attachment_ids'] = [(4, id) for id in template_values.get('attachment_ids', [])]
                    composer.write(template_values)
                    composer.send_mail()
        return True

    @api.multi
    def invoice_validate(self):
        res = super(AccountInvoice, self).invoice_validate()
        self.invoice_validate_send_email()
        return res
