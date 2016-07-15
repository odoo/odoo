from openerp.osv import osv


class mail_mail(osv.Model):
    _name = 'mail.mail'
    _inherit = 'mail.mail'

    def _postprocess_sent_message(self, cr, uid, ids, context=None, mail_sent=True):
        for mail in self.browse(cr, uid, ids, context=context):
            if mail_sent and mail.model == 'purchase.order':
                obj = self.pool.get('purchase.order').browse(cr, uid, mail.res_id, context=context)
                if obj.state == 'draft':
                    self.pool.get('purchase.order').signal_workflow(cr, uid, [mail.res_id], 'send_rfq')
        return super(mail_mail, self)._postprocess_sent_message(cr, uid, ids, context=context, mail_sent=mail_sent)
