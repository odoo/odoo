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

from report.interface import report_int
import netsvc

class auction_invoice(report_int):
    def __init__(self, name):
        report_int.__init__(self, name)

    def create(self,cr, uid, ids, datas, context):
        lots = self.pool.get('auction.lots').read(cr, uid, ids, ['ach_inv_id'], context=context)

        invoices = {}
        for l in lots:
            if l['ach_inv_id']:
                invoices[l['ach_inv_id'][0]]=True
        new_ids = invoices.keys()
        if not len(new_ids):
            raise 'UserError', 'Objects not Invoiced !'

        datas['ids'] = new_ids

        self._obj_invoice = netsvc.LocalService('report.account.invoice')
        return self._obj_invoice.create(cr, uid, new_ids, datas, context)

    def result(self):
        return self._obj_invoice.result()

auction_invoice('report.auction.invoice')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

