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

from openerp.report import report_sxw
from openerp.osv import osv
from openerp.tools.translate import _

class pos_invoice(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(pos_invoice, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
        })

    def set_context(self, objects, data, ids, report_type=None):
        super(pos_invoice, self).set_context(objects, data, ids, report_type)
        iids = []
        nids = []

        for order in objects:
            order.write({'nb_print': order.nb_print + 1})

            if order.invoice_id and order.invoice_id not in iids:
                if not order.invoice_id:
                    raise osv.except_osv(_('Error!'), _('Please create an invoice for this sale.'))
                iids.append(order.invoice_id)
                nids.append(order.invoice_id.id)
        data['ids'] = nids
        self.datas = data
        self.ids = nids
        self.objects = iids
        self.localcontext['data'] = data
        self.localcontext['objects'] = iids

report_sxw.report_sxw('report.pos.invoice', 'pos.order', 'addons/account/report/account_print_invoice.rml', parser= pos_invoice)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
