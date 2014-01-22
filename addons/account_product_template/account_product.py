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
from openerp.osv import fields, osv

class product_template(osv.osv):
    _inherit = "product.template"
    _columns = {
        'email_template_id': fields.many2one('email.template','Product Email Template'),
    }

class account_invoice(osv.Model):
    _inherit = 'account.invoice'

    def invoice_validate(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mail_obj = self.pool.get('mail.compose.message')
        res = super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)
        for line in self.browse(cr, uid, ids[0], context=context).invoice_line:
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
