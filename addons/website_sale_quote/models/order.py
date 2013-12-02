# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
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

from openerp.osv import osv, fields
import hashlib
import time

class sale_quote(osv.Model):
    _name = "sale.quote"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Sales Quotations"
    _columns = {
#            'template_id': fields.many2one('ir.ui.view', 'Template'),
            'order_id': fields.many2one('sale.order', 'Order', required=True),
            'state': fields.selection([
            ('draft', 'Draft Quotation'),
            ('sent', 'Quotation Sent'),
            ('accept', 'Accept'),
            ('cancel', 'Cancelled'),
            ('done', 'Done'),
            ], 'Status'),
            'to_email': fields.char('Customers Email'),
            'access_token':fields.char('Quotation Token', size=256),
    }

    def new_quotation_token(self, cr, uid, record_id):
        db_uuid = self.pool.get('ir.config_parameter').get_param(cr, uid, 'database.uuid')
        quotation_token = hashlib.sha256('%s-%s-%s' % (time.time(), db_uuid, record_id)).hexdigest()
        return self.write(cr, uid, [record_id],{'access_token': quotation_token} )

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        new_id = super(sale_quote, self).create(cr, uid, vals, context=context)
        self.new_quotation_token(cr, uid, new_id)
        return new_id


class sale_order(osv.osv):
    _inherit = 'sale.order'
    _columns = {
        'quote_url': fields.char('URL'),
    }

#    def action_quotation_send(self, cr, uid, ids, context=None):
#        '''
#        This function opens a window to compose an email, with the edi sale template message loaded by default
#        '''
#        data_pool = self.pool.get('ir.model.data')
#        sale_quote = self.pool.get('sale.quote')
#        try:
#            compose_form_id = data_pool.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
#        except ValueError:
#            compose_form_id = False
#        model,template_id = data_pool.get_object_reference(cr, uid, 'website_sale_quote', "email_template_sale_quote")
#        ctx = dict(context)
#        for order in self.browse(cr, uid, ids, context):
#            if not order.quote_id:
#                new_id = sale_quote.create(cr, uid,{
#                    'state' : 'draft',
#                    'to_email': order.partner_id.email,
#                })
#                self.write(cr, uid, [order.id] ,{'quote_id': new_id}, context)
#            ctx.update({
#                'default_model': 'sale.order',
#                'default_res_id': order.id,
#                'default_use_template': bool(template_id),
#                'default_template_id': template_id,
#                'default_composition_mode': 'comment',
#                'mark_so_as_sent': True
#            })
#        return {
#            'type': 'ir.actions.act_window',
#            'view_type': 'form',
#            'view_mode': 'form',
#            'res_model': 'mail.compose.message',
#            'views': [(compose_form_id, 'form')],
#            'view_id': compose_form_id,
#            'target': 'new',
#            'context': ctx,
#        }

    def action_quotation_send(self, cr, uid, ids, context=None):
        quote = super(sale_order, self).action_quotation_send(cr, uid,ids, context)
        sale_quote = self.pool.get('sale.quote')
        for order in self.browse(cr, uid, ids, context):
            q_id = sale_quote.search(cr, uid, [('order_id','=', order.id)], context=context)
            if not q_id:
                new_id = sale_quote.create(cr, uid,{
                    'order_id' : order.id,
                    'state' : 'draft',
                    'to_email': order.partner_id.email,
                })
                self.write(cr, uid, order.id, {'quote_url': self.get_signup_url(cr, uid, [order.id], context)})
        return quote

    def get_signup_url(self, cr, uid, ids, context=None):
        url = False
        quote_id = self.pool.get('sale.quote').search(cr, uid, [('order_id','=', ids[0])], context=context)
        for quote in self.pool.get('sale.quote').browse(cr, uid, quote_id, context=context):
            base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url', default='http://localhost:8069', context=context)
            url = "%s/quote/%s" % (base_url, quote.access_token)
        return url
