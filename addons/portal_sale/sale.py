# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv

class sale_order(osv.osv):
    _inherit = 'sale.order'

    def action_button_confirm(self, cr, uid, ids, context=None):
        # fetch the partner's id and subscribe the partner to the sale order
        partner = self.browse(cr, uid, ids[0], context=context)['partner_id']
        if partner.id not in self.browse(cr, uid, ids[0], context=context)['message_follower_ids']:
            self.message_subscribe(cr, uid, ids, [partner.id], context=context)
            document = self.browse(cr, uid, ids[0], context=context)
            mail_values = {
                'email_from': self.pool.get('res.users').browse(cr, uid, uid, context=context)['partner_id']['email'],
                'email_to': partner.email,
                'subject': 'Invitation to follow %s' % document.name_get()[0][1],
                'body_html': 'You have been invited to follow %s' % document.name_get()[0][1],
                'auto_delete': True,
            }
            mail_obj = self.pool.get('mail.mail')
            mail_id = mail_obj.create(cr, uid, mail_values, context=context)
            mail_obj.send(cr, uid, [mail_id], recipient_ids=[partner.id], context=context)
        return super(sale_order, self).action_button_confirm(cr, uid, ids, context=context)

sale_order()

class mail_mail(osv.osv):
    _inherit = 'mail.mail'

    def _postprocess_sent_message(self, cr, uid, mail, context=None):
        if mail.model == 'sale.order':
            so_obj = self.pool.get('sale.order')
            partner = so_obj.browse(cr, uid, mail.res_id, context=context)['partner_id']
            # Add the customer in the SO as follower
            if partner.id not in so_obj.browse(cr, uid, mail.res_id, context=context)['message_follower_ids']:
                so_obj.message_subscribe(cr, uid, [mail.res_id], [partner.id], context=context)
            # Add all recipients of the email as followers
            for p in mail.partner_ids:
                if p.id not in so_obj.browse(cr, uid, mail.res_id, context=context)['message_follower_ids']:
                    so_obj.message_subscribe(cr, uid, [mail.res_id], [p.id], context=context)
        return super(mail_mail, self)._postprocess_sent_message(cr, uid, mail=mail, context=context)

mail_mail()