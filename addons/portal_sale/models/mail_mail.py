from openerp.osv import osv


class mail_mail(osv.osv):
    _inherit = 'mail.mail'

    def _postprocess_sent_message(self, cr, uid, mail, context=None, mail_sent=True):
        if mail_sent and mail.model == 'sale.order':
            so_obj = self.pool.get('sale.order')
            order = so_obj.browse(cr, uid, mail.res_id, context=context)
            partner = order.partner_id
            # Add the customer in the SO as follower
            if partner not in order.message_partner_ids:
                so_obj.message_subscribe(cr, uid, [mail.res_id], [partner.id], context=context)
            # Add all recipients of the email as followers
            for p in mail.partner_ids:
                if p not in order.message_partner_ids:
                    so_obj.message_subscribe(cr, uid, [mail.res_id], [p.id], context=context)
        return super(mail_mail, self)._postprocess_sent_message(cr, uid, mail=mail, context=context, mail_sent=mail_sent)
