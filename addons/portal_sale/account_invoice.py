# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 OpenERP S.A (<http://www.openerp.com>).
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

from osv import fields,osv

class mail_mail(osv.osv):
    _inherit = 'mail.mail'

    def _postprocess_sent_message(self, cr, uid, mail, context=None):
        if mail.model == 'account.invoice':
            so_obj = self.pool.get('sale.order')
            inv_obj = self.pool.get('account.invoice')

            inv_follower_ids = inv_obj.read(cr, uid, mail.res_id, ['message_follower_ids'], context=context)['message_follower_ids']

            cr.execute('SELECT rel.order_id FROM sale_order_invoice_rel AS rel WHERE rel.invoice_id='+str(mail.res_id))
            so_invoice_ids = cr.fetchall()        
            so_follower_ids = []
            for so_invoice_id in so_invoice_ids:
                order_id, = so_invoice_id
                so_follower_ids += so_obj.read(cr, uid, order_id, ['message_follower_ids'], context=context)['message_follower_ids']

            partner_ids = list(set(so_follower_ids).difference(set(inv_follower_ids)))

            if partner_ids:
                partner_obj = self.pool.get('res.partner')
                user_obj = self.pool.get('res.users')
                group_obj = self.pool.get('res.groups')

                document = inv_obj.browse(cr, uid, mail.res_id, context=context)

                # partners = partner_obj.read(cr, uid, partner_ids, ['user_ids'], context=context)
                # for partner in partners:
                #     users = user_obj.read(cr, uid, partner['user_ids'], ['groups_id'], context=context)
                #     for user in users:                    
                #         for group in group_obj.browse(cr, uid, user['groups_id'], context=context):
                #             if group.is_portal == True:
                #                 print 'Hello'
                                # inv_obj.message_subscribe(cr, uid, [mail.res_id], partner_ids, context=context)
                                # mail_values = {
                                #     'email_from': 'vta@openerp.com',
                                #     'email_to': 'falcobolger@gmail.com',
                                #     'subject': 'Invitation to follow %s' % document.name_get()[0][1],
                                #     'body_html': 'You have been invited to follow %s' % document.name_get()[0][1],
                                #     'auto_delete': True,
                                # }
                                # mail_id = self.create(cr, uid, mail_values, context=context)
                                # print mail_values
                                # self.send(cr, uid, [mail_id], recipient_ids=[partner['id']], context=context)
                                
        return super(mail_mail, self)._postprocess_sent_message(cr, uid, mail=mail, context=context)

mail_mail()