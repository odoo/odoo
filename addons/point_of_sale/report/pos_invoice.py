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


class pos_invoice(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(pos_invoice, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
        })

    def preprocess(self, objects, data, ids):
        super(pos_invoice, self).preprocess(objects, data, ids)

        post_objects = []
        for obj in objects:
            if obj.invoice_id:
                post_objects.append(obj.invoice_id)

        #self.localcontext['objects'] = objects
        self.localcontext['objects'] = post_objects


report_sxw.report_sxw(
    'report.pos.invoice',
    'pos.order',
    'addons/point_of_sale/report/pos_invoice.rml',
    parser=pos_invoice)

