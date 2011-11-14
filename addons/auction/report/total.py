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
import netsvc

from report.interface import report_rml

def toxml(val):
    return val.replace('&', '&amp;').replace('<','&lt;').replace('>','&gt;').decode('utf-8').encode('latin1')

class report_custom(report_rml):
    def __init__(self, name, table, tmpl, xsl):
        report_rml.__init__(self, name, table, tmpl, xsl)

    def create_xml(self, cr, uid, ids, datas, context=None):
        lots = self.pool.get('auction.lots').read(cr, uid , ids, ['obj_price','ach_login','obj_comm','lot_est1','lot_est2','bord_vnd_id','ach_emp','auction_id'])
        auction = self.pool.get('auction.dates').read(cr, uid, [lots[0]['auction_id'][0]])[0]

        unsold = comm = emp = paid = unpaid = 0
        est1 = est2 = adj = 0
        paid_ids = []
        unpaid_ids = []
        buyer = {}
        seller = {}

        for l in lots:
            if l['lot_est2']:
                est2 += l['lot_est2'] or 0.0

            if l['lot_est1']:
                est1 += l['lot_est1'] or 0.0

            if l['obj_price']:
                adj += l['obj_price'] or 0.0

            if l['obj_comm']:
                comm += 1

            if l['ach_emp']:
                emp += 1

            if l['ach_pay_id']:
                paid_ids.append(l['id'])
                paid += l['obj_price']
            else:
                unpaid_ids.append(l['id'])
                unpaid += l['obj_price']

            if l['obj_price']==0:
                unsold+=1

            buyer[l['ach_login']]=1
            seller[l['bord_vnd_id']]=1


        debit = adj
        costs = self.pool.get('auction.lots').compute_seller_costs(cr, uid, ids)
        for cost in costs:
            debit += cost['amount']


        xml = '''<?xml version="1.0" encoding="ISO-8859-1"?>
<report>
    <date>%s</date>
    <auction>
        <title>%s</title>
        <date>%s</date>
    </auction>
    <objects>
        <obj_nbr>%d</obj_nbr>
        <est_min>%.2f</est_min>
        <est_max>%.2f</est_max>
        <unsold>%d</unsold>
        <obj_price>%.2f</obj_price>
    </objects>
    <buyer>
        <buy_nbr>%d</buy_nbr>
        <paid_nbr>%d</paid_nbr>
        <comm_nbr>%d</comm_nbr>
        <taken_nbr>%d</taken_nbr>
        <credit>%.2f</credit>
        <paid>%.2f</paid>
    </buyer>
    <seller>
        <sell_nbr>%d</sell_nbr>
        <debit>%.2f</debit>
    </seller>
</report>''' % (time.strftime('%d/%m/%Y'), toxml(auction['name']), auction['auction1'], len(lots), est1, est2, unsold, adj, len(buyer), len(paid_ids), comm, emp, unpaid, paid, len(seller), debit)

        return self.post_process_xml_data(cr, uid, xml, context)

report_custom('report.auction.total', 'auction.lots', '', 'addons/auction/report/total.xsl')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

