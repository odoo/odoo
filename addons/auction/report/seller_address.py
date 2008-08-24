# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from report.interface import report_int
import netsvc

class auction_seller(report_int):
    def __init__(self, name):
        report_int.__init__(self, name)

    def create(self,cr, uid, ids, datas, context):
        service = netsvc.LocalService("object_proxy")
        lots = service.execute(cr.dbname,uid, 'auction.lots', 'read', ids, ['bord_vnd_id'])

        bords = {}
        for l in lots:
            if l['bord_vnd_id']:
                bords[l['bord_vnd_id'][0]]=True
        new_ids = bords.keys()

        parts = {}
        partners = service.execute(cr.dbname,uid, 'auction.deposit', 'read', new_ids, ['partner_id'])
        for l in partners:
            if l['partner_id']:
                parts[l['partner_id'][0]]=True
        new_ids = parts.keys()
        if not len(new_ids):
            raise 'UserError', 'No seller !'

        datas['ids'] = new_ids

        self._obj_invoice = netsvc.LocalService('report.res.partner.address')
        return self._obj_invoice.create(cr,uid, new_ids, datas, context)

    def result(self):
        return self._obj_invoice.result()

auction_seller('report.auction.seller_labels')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

