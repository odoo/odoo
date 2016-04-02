# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from openerp.osv import fields, osv
from openerp.tools.translate import _


class product_margin(osv.osv_memory):
    _name = 'product.margin'
    _description = 'Product Margin'
    _columns = {
        'from_date': fields.date('From'),
        'to_date': fields.date('To'),
        'invoice_state': fields.selection([
            ('paid', 'Paid'),
            ('open_paid', 'Open and Paid'),
            ('draft_open_paid', 'Draft, Open and Paid'),
        ], 'Invoice State', select=True, required=True),
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
        context = dict(context or {})

        def ref(module, xml_id):
            proxy = self.pool.get('ir.model.data')
            return proxy.get_object_reference(cr, uid, module, xml_id)

        model, search_view_id = ref('product', 'product_search_form_view')
        model, graph_view_id = ref('product_margin', 'view_product_margin_graph')
        model, form_view_id = ref('product_margin', 'view_product_margin_form')
        model, tree_view_id = ref('product_margin', 'view_product_margin_tree')

        #get the current product.margin object to obtain the values from it
        records = self.browse(cr, uid, ids, context=context)
        record = records[0]

        context.update(invoice_state=record.invoice_state)

        if record.from_date:
            context.update(date_from=record.from_date)

        if record.to_date:
            context.update(date_to=record.to_date)

        views = [
            (tree_view_id, 'tree'),
            (form_view_id, 'form'),
            (graph_view_id, 'graph')
        ]
        return {
            'name': _('Product Margins'),
            'context': context,
            'view_type': 'form',
            "view_mode": 'tree,form,graph',
            'res_model': 'product.product',
            'type': 'ir.actions.act_window',
            'views': views,
            'view_id': False,
            'search_view_id': search_view_id,
        }
