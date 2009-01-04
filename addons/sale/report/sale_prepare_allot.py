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

class sale_prepare(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(sale_prepare, self).__init__(cr, uid, name, context)
        self.localcontext.update( {
            'allotment': self._allotment,
        })
        
    def _allotment(self, object):
        allotments = {}
        for line in object.order_line:
            if line.address_allotment_id:
                allotments.setdefault(line.address_allotment_id.id, ([line.address_allotment_id],[]) )
            else:
                allotments.setdefault(line.address_allotment_id.id, ([],[]) )
            allotments[line.address_allotment_id.id][1].append(line)
        return allotments.values()

report_sxw.report_sxw('report.sale.order.prepare.allot', 'sale.order', 'addons/sale/report/prepare_allot.rml',parser=sale_prepare)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

