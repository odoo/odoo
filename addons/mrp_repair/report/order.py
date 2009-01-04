# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from report import report_sxw
from osv import osv
import pooler

class order(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(order, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'total': self.total,
            'adr_get' : self._adr_get
        })


    def total(self, repair):
        total = 0.0
        for operation in repair.operations:
           total+=operation.price_subtotal
        for fee in repair.fees_lines:
           total+=fee.price_subtotal
        total = total + repair.amount_tax
        return total

    def _adr_get(self, partner, type):
            res_partner = pooler.get_pool(self.cr.dbname).get('res.partner')
            res_partner_address = pooler.get_pool(self.cr.dbname).get('res.partner.address')
            addresses = res_partner.address_get(self.cr, self.uid, [partner.id], [type])
            adr_id = addresses and addresses[type] or False
            return adr_id and res_partner_address.read(self.cr, self.uid, [adr_id])[0] or False

report_sxw.report_sxw('report.repair.order','mrp.repair','addons/mrp_repair/report/order.rml',parser=order)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

