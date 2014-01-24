# -*- coding: utf-8 -*-

from openerp.osv import osv


class account_invoice(osv.Model):
    _inherit = 'account.invoice'

    def invoice_validate(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mail_msg_obj = self.pool['mail.compose.message']
        template_obj = self.pool['email.template']
        res = super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)
        for invoice in self.browse(cr, uid, ids, context=context):
            # send template only on customer invoice
            if invoice.type != 'out_invoice':
                continue
            # subscribe the partner to the invoice
            if invoice.partner_id.id not in invoice.message_follower_ids:
                self.message_subscribe(cr, uid, [invoice.id], [invoice.partner_id.id], context=context)
            for line in invoice.invoice_line:
                if line.product_id.email_template_id:
                    template_res = template_obj.get_email_template_batch(cr, uid, template_id=line.product_id.email_template_id.id, res_ids=[line.product_id.product_tmpl_id.id], context=context)
                    mail = template_res[line.product_id.product_tmpl_id.id]
                    message_wiz_id = mail_msg_obj.create(cr, uid, {
                        'model': 'account.invoice',
                        'res_id': invoice.id,
                        'body': mail.body_html,
                    }, context=context)
                    mail_msg_obj.send_mail(cr, uid, [message_wiz_id], context=context)
        return res
