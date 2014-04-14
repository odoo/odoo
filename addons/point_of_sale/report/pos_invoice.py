# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today OpenERP SA (<http://www.openerp.com>).
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

from openerp.osv import osv
from openerp.tools.translate import _


class PosInvoiceReport(osv.AbstractModel):
    _name = 'report.point_of_sale.report_invoice'

    def render_html(self, cr, uid, ids, data=None, context=None):
        if context is None:
            context = {}

        report_obj = self.pool['report']
        report = report_obj._get_report_from_name(cr, uid, 'account.report_invoice')
        selected_posorders = self.pool['pos.order'].browse(cr, uid, ids, context=context)

        invoiced_posorders = []
        invoiced_posorders_ids = []
        for order in selected_posorders:
            if order.invoice_id:
                invoiced_posorders.append(order)
                invoiced_posorders_ids.append(order.id)

        if not invoiced_posorders:
            raise osv.except_osv(_('Error!'), _('Please create an invoice for this sale.'))

        docargs = {
            'doc_ids': invoiced_posorders_ids,
            'doc_model': report.model,
            'docs': invoiced_posorders,
        }
        return report_obj.render(cr, uid, invoiced_posorders_ids, 'account.report_invoice', docargs, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
