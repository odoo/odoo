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
import openerp.pooler

class auction_seller(report_int):
    def __init__(self, name):
        report_int.__init__(self, name)

    def create(self, cr, uid, ids, datas, context):
        pool = openerp.pooler.get_pool(cr.dbname)
        lots = pool.get('auction.lots').read(cr, uid, ids, ['bord_vnd_id'])

        bords = {}
        for l in lots:
            if l['bord_vnd_id']:
                bords[l['bord_vnd_id'][0]]=True
        new_ids = bords.keys()

        parts = {}
        partners = pool.get('auction.deposit').read(cr, uid, new_ids, ['partner_id'])
        for l in partners:
            if l['partner_id']:
                parts[l['partner_id'][0]]=True
        new_ids = parts.keys()
        if not len(new_ids):
            raise 'UserError', 'No seller !'

        datas['ids'] = new_ids

        self._obj_invoice = netsvc.LocalService('report.res.partner.address')
        return self._obj_invoice.create(cr, uid, new_ids, datas, context)

    def result(self):
        return self._obj_invoice.result()

auction_seller('report.auction.seller_labels')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

