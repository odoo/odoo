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


import time
from report import report_sxw

class seller_form_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(seller_form_report, self).__init__(cr, uid, name, context=context)

        self.localcontext.update({
            'time': time,
            'sum_taxes': self.sum_taxes,
            'sellerinfo' : self.seller_info,
            'grand_total' : self.grand_seller_total,
    })


    def sum_taxes(self, lot):
        taxes=[]
        amount=0.0
        if lot.bord_vnd_id.tax_id:
            taxes.append(lot.bord_vnd_id.tax_id)
        elif lot.auction_id and lot.auction_id.seller_costs:
            taxes += lot.auction_id.seller_costs
        tax=self.pool.get('account.tax').compute_all(self.cr, self.uid, taxes, lot.obj_price, 1)
        for t in tax:
            amount+=t['amount']
        return amount
    def seller_info(self):
        objects = [object for object in self.localcontext.get('objects')]
        ret_dict = {}
        for object in objects:

            partner = ret_dict.get(object.bord_vnd_id.partner_id.id,False)
            if not partner:
                ret_dict[object.bord_vnd_id.partner_id.id] = {'partner' : object.bord_vnd_id.partner_id or False,'lots':[object]}
            else:
                lots = partner.get('lots')
                lots.append(object)
        return ret_dict.values()
    def grand_seller_total(self,o):
        grand_total = 0
        for oo in o:
            grand_total =grand_total + oo['obj_price']+ self.sum_taxes(oo)
        return grand_total


report_sxw.report_sxw('report.seller_form_report', 'auction.lots', 'addons/auction/report/seller_form_report.rml', parser=seller_form_report)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

