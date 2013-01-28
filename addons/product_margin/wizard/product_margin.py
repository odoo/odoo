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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class product_margin(osv.osv_memory):
    _name = 'product.margin'
    _description = 'Product Margin'
    _columns = {
        'from_date': fields.date('From'),
        'to_date': fields.date('To'),
        'invoice_state':fields.selection([
           ('paid','Paid'),
           ('open_paid','Open and Paid'),
           ('draft_open_paid','Draft, Open and Paid'),
        ],'Invoice State', select=True, required=True),
    }
    _defaults = {
        'from_date': time.strftime('%Y-01-01'),
        'to_date': time.strftime('%Y-12-31'),
        'invoice_state': "open_paid",
    }
    def action_open_window(self, cr, uid, ids, context=None):
        """
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: the ID or list of IDs if we want more than one

            @return:
        """
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        result = mod_obj._get_id(cr, uid, 'product', 'product_search_form_view')
        id = mod_obj.read(cr, uid, result, ['res_id'], context=context)
        cr.execute('select id,name from ir_ui_view where name=%s and type=%s', ('product.margin.graph', 'graph'))
        view_res3 = cr.fetchone()[0]
        cr.execute('select id,name from ir_ui_view where name=%s and type=%s', ('product.margin.form.inherit', 'form'))
        view_res2 = cr.fetchone()[0]
        cr.execute('select id,name from ir_ui_view where name=%s and type=%s', ('product.margin.tree', 'tree'))
        view_res = cr.fetchone()[0]

        #get the current product.margin object to obtain the values from it
        product_margin_obj = self.browse(cr, uid, ids, context=context)[0]

        context.update(invoice_state = product_margin_obj.invoice_state)
        if product_margin_obj.from_date:
            context.update(date_from = product_margin_obj.from_date)
        if product_margin_obj.to_date:
            context.update(date_to = product_margin_obj.to_date)
        return {
            'name': _('Product Margins'),
            'context': context,
            'view_type': 'form',
            "view_mode": 'tree,form,graph',
            'res_model':'product.product',
            'type': 'ir.actions.act_window',
            'views': [(view_res,'tree'), (view_res2,'form'), (view_res3,'graph')],
            'view_id': False,
            'search_view_id': id['res_id']
        }

product_margin()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
