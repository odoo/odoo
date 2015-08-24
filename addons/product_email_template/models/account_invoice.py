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
            if invoice.partner_id not in invoice.message_partner_ids:
                self.message_subscribe(cr, uid, [invoice.id], [invoice.partner_id.id], context=context)
            for line in invoice.invoice_line_ids:
                if line.product_id.email_template_id:
                    invoice.message_post_with_template(line.product_id.email_template_id.id, composition_mode='comment')
        return True

    def invoice_validate(self, cr, uid, ids, context=None):
        res = super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)
        self.invoice_validate_send_email(cr, uid, ids, context=context)
        return res
