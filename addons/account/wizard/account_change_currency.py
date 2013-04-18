# -*- encoding: utf-8 -*-
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
from openerp.tools.translate import _

class account_change_currency(osv.osv_memory):
    _name = 'account.change.currency'
    _description = 'Change Currency'
    _columns = {
       'currency_id': fields.many2one('res.currency', 'Change to', required=True, help="Select a currency to apply on the invoice"),
    }

    def view_init(self, cr , uid , fields_list, context=None):
        obj_inv = self.pool.get('account.invoice')
        if context is None:
            context = {}
        if context.get('active_id',False):
            if obj_inv.browse(cr, uid, context['active_id']).state != 'draft':
                raise osv.except_osv(_('Error!'), _('You can only change currency for Draft Invoice.'))
            pass

    def change_currency(self, cr, uid, ids, context=None):
        obj_inv = self.pool.get('account.invoice')
        obj_inv_line = self.pool.get('account.invoice.line')
        obj_currency = self.pool.get('res.currency')
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids, context=context)[0]
        new_currency = data.currency_id.id

        invoice = obj_inv.browse(cr, uid, context['active_id'], context=context)
        if invoice.currency_id.id == new_currency:
            return {}
        rate = obj_currency.browse(cr, uid, new_currency, context=context).rate
        for line in invoice.invoice_line:
            new_price = 0
            if invoice.company_id.currency_id.id == invoice.currency_id.id:
                new_price = line.price_unit * rate
                if new_price <= 0:
                    raise osv.except_osv(_('Error!'), _('New currency is not configured properly.'))

            if invoice.company_id.currency_id.id != invoice.currency_id.id and invoice.company_id.currency_id.id == new_currency:
                old_rate = invoice.currency_id.rate
                if old_rate <= 0:
                    raise osv.except_osv(_('Error!'), _('Current currency is not configured properly.'))
                new_price = line.price_unit / old_rate

            if invoice.company_id.currency_id.id != invoice.currency_id.id and invoice.company_id.currency_id.id != new_currency:
                old_rate = invoice.currency_id.rate
                if old_rate <= 0:
                    raise osv.except_osv(_('Error!'), _('Current currency is not configured properly.'))
                new_price = (line.price_unit / old_rate ) * rate
            obj_inv_line.write(cr, uid, [line.id], {'price_unit': new_price})
        obj_inv.write(cr, uid, [invoice.id], {'currency_id': new_currency}, context=context)
        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
