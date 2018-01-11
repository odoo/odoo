# -*- coding: utf-8 -*-

from openerp.osv import osv


class account_invoice(osv.Model):
    _inherit = 'account.invoice'

    def invoice_validate_send_email(self, cr, uid, ids, context=None):
        Composer = self.pool['mail.compose.message']
        for invoice in self.browse(cr, uid, ids, context=context):
            # send template only on customer invoice
            if invoice.type != 'out_invoice':
                continue
            # subscribe the partner to the invoice
            if invoice.partner_id not in invoice.message_follower_ids:
                self.message_subscribe(cr, uid, [invoice.id], [invoice.partner_id.id], context=context)
            for line in invoice.invoice_line:
                if line.product_id.email_template_id:
                    # CLEANME: should define and use a clean API: message_post with a template
                    composer_id = Composer.create(cr, uid, {
                        'model': 'account.invoice',
                        'res_id': invoice.id,
                        'template_id': line.product_id.email_template_id.id,
                        'composition_mode': 'comment',
                    }, context=context)
                    template_values = Composer.onchange_template_id(
                        cr, uid, composer_id, line.product_id.email_template_id.id, 'comment', 'account.invoice', invoice.id
                    )['value']
                    template_values['attachment_ids'] = [(4, id) for id in template_values.get('attachment_ids', [])]
                    Composer.write(cr, uid, [composer_id], template_values, context=context)
                    Composer.send_mail(cr, uid, [composer_id], context=context)
        return True

    def invoice_validate(self, cr, uid, ids, context=None):
        res = super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)
        self.invoice_validate_send_email(cr, uid, ids, context=context)
        return res
