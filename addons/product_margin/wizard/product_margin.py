# -*- coding: utf-8 -*-

from datetime import date

from openerp import api, fields, models, _


class ProductMargin(models.TransientModel):
    _name = 'product.margin'
    _description = 'Product Margin'
    _rec_name = 'from_date'

    from_date = fields.Date(string='From', default=fields.Date.to_string(date(date.today().year, 1, 1)))
    to_date = fields.Date(string='To', default=fields.Date.to_string(date(date.today().year, 12, 31)))
    invoice_state = fields.Selection([
        ('paid', 'Paid'),
        ('open_paid', 'Open and Paid'),
        ('draft_open_paid', 'Draft, Open and Paid'),
    ], index=True, required=True, default="open_paid")

    @api.multi
    def action_open_window(self):
        context = dict(self.env.context)

        search_view_id = self.env.ref('product.product_search_form_view').id
        graph_view_id = self.env.ref('product_margin.view_product_margin_graph').id
        form_view_id = self.env.ref('product_margin.view_product_margin_form').id
        tree_view_id = self.env.ref('product_margin.view_product_margin_tree').id

        context.update(invoice_state=self.invoice_state, from_date=self.from_date, to_date=self.to_date)
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
