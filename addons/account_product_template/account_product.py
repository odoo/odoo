# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today OpenERP SA (<http://www.openerp.com>).
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
from openerp.osv import fields, osv

class product_template(osv.osv):
    _inherit = "product.template"
    _columns = {
        'email_template_id': fields.many2one('email.template','Product Email Template'),
    }

class email_template(osv.osv):
    _inherit = 'email.template'

    def default_get(self, cr, uid, fields, context=None):
        res = super(email_template, self).default_get(cr, uid, fields, context)
        if context.get('form_view_ref') == 'account_product_template.view_email_template_form_product':
            res['email_from'] = '${(user.email)|safe}'
            res['email_to'] = '${(object.partner_id.email)|safe}'
            res['partner_to'] = '${object.partner_id.id}'
            res['name'] = context.get('product_name')
            res['subject'] = context.get('product_name')
            res['model_id'] = self.pool.get('ir.model').search(cr, uid, [('model', '=', 'account.invoice')], context=context)
        return res

class account_invoice(osv.Model):
    _inherit = 'account.invoice'

    def invoice_validate(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mail_obj = self.pool.get('mail.compose.message')
        res = super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)
        invoice = self.browse(cr, uid, ids[0], context=context)
        for line in invoice.invoice_line:
            # fetch the partner's id and subscribe the partner to the invoice
            if invoice.partner_id.id not in invoice.message_follower_ids:
                self.message_subscribe(cr, uid, [invoice.id], [invoice.partner_id.id], context=context)
            if line.product_id.email_template_id:
                message_wiz_id = mail_obj.create(cr, uid, {
                    'model': 'account.invoice',
                    'res_id': ids[0],
                    'template_id': line.product_id.email_template_id.id,
                    'body': line.product_id.email_template_id.body_html
                }, context=context)
                mail_obj.send_mail(cr, uid, [message_wiz_id], context=context)
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
