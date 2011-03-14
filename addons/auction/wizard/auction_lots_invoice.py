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

from osv import osv, fields
import netsvc
from tools.translate import _

class auction_lots_invoice(osv.osv_memory):
    _name = 'auction.lots.invoice'
    _description = "Auction Lots Invoice"

    _columns = {
        'amount': fields.float('Invoiced Amount', required=True, readonly=True),
        'amount_topay': fields.float('Amount to pay', required=True, readonly=True),
        'amount_paid': fields.float('Amount paid', readonly=True),
        'objects': fields.integer('# of objects', required=True, readonly=True),
        'ach_uid': fields.many2one('res.partner','Buyer Name', required=True ),
        'number': fields.integer('Invoice Number'),
    }

    def default_get(self, cr, uid, fields, context=None):
        """
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary which of fields with values.
        """
        if context is None: 
            context = {}
        res = super(auction_lots_invoice, self).default_get(cr, uid, fields, context=context)
        service = netsvc.LocalService("object_proxy")
        lots = service.execute(cr.dbname, uid, 'auction.lots', 'read', context.get('active_ids', []))
        auction = service.execute(cr.dbname, uid, 'auction.dates', 'read', [lots[0]['auction_id'][0]])[0]

        price = 0.0
        price_topay = 0.0
        price_paid = 0.0
        for lot in lots:
            price_lot = lot['obj_price'] or 0.0

            costs = service.execute(cr.dbname, uid, 'auction.lots', 'compute_buyer_costs', [lot['id']])
            price_lot += costs['amount']
            price += price_lot

            if lot['ach_uid']:
                if uid and (lot['ach_uid'][0]<>uid):
                    raise osv.except_osv(_('UserError'), _('Two different buyers for the same invoice !\nPlease correct this problem before invoicing'))
                uid = lot['ach_uid'][0]
            elif lot['ach_login']:
                refs = service.execute(uid, 'res.partner', 'search', [('ref','=',lot['ach_login'])])
                if len(refs):
                    uid = refs[-1]
            if 'ach_pay_id' in lot and lot['ach_pay_id']:
                price_paid += price_lot
                #*tax
            else:
                price_topay += price_lot
                #*tax

    #TODO: recuperer id next invoice (de la sequence)???
        invoice_number = False
        for lot in self.pool.get('auction.lots').browse(cr, uid, context.get('active_ids', []), context=context):
            if 'objects' in fields:
                res.update({'objects':len(context.get('active_ids', []))})
            if 'amount' in fields:
                res.update({'amount': price})
            if 'ach_uid' in fields:
                res.update({'ach_uid': uid})
            if 'amount_topay' in fields:
                res.update({'amount_topay':price_topay})
            if 'amount_paid' in fields:
                res.update({'amount_paid':price_paid})
            if 'number' in fields:
                res.update({'number':invoice_number})
        return res

    def print_report(self, cr, uid, ids, context=None):
        """
        Create an invoice report.
        @param cr: the current row, from the database cursor.
        @param uid: the current user’s ID for security checks.
        @param ids: List of Auction lots make invoice buyer’s IDs
        @return: dictionary of  account invoice form.
        """
        if context is None: 
            context = {}
        service = netsvc.LocalService("object_proxy")
        datas = {'ids' : context.get('active_ids',[])}
        res = self.read(cr, uid, ids, ['number','ach_uid'])
        res = res and res[0] or {}
        datas['form'] = res
        return {
            'type' : 'ir.actions.report.xml',
            'report_name':'auction.invoice',
            'datas' : datas,
        }

auction_lots_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
