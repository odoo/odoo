# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _


class ProductMargin(models.TransientModel):
    _name = 'product.margin'
    _description = 'Product Margin'

    from_date = fields.Date('From', default=time.strftime('%Y-01-01'))
    to_date = fields.Date('To', default=time.strftime('%Y-12-31'))
    invoice_state = fields.Selection([
        ('paid', 'Paid'),
        ('open_paid', 'Open and Paid'),
        ('draft_open_paid', 'Draft, Open and Paid'),
    ], 'Invoice State', index=True, required=True, default="open_paid")

    @api.multi
    def action_open_window(self):
        self.ensure_one()
        context = dict(self.env.context or {})

        def ref(module, xml_id):
            proxy = self.env['ir.model.data']
            return proxy.get_object_reference(module, xml_id)

        model, search_view_id = ref('product', 'product_search_form_view')
        model, graph_view_id = ref('product_margin', 'view_product_margin_graph')
        model, form_view_id = ref('product_margin', 'view_product_margin_form')
        model, tree_view_id = ref('product_margin', 'view_product_margin_tree')

        context.update(invoice_state=self.invoice_state)

        if self.from_date:
            context.update(date_from=self.from_date)

        if self.to_date:
            context.update(date_to=self.to_date)

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
