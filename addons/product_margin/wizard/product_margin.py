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
    ], 'Invoice State', required=True, default="open_paid")

    def action_open_window(self):
        self.ensure_one()
        context = dict(self.env.context, create=False, edit=False)

        def ref(xml_id):
            proxy = self.env['ir.model.data']
            return proxy._xmlid_lookup(xml_id)[2]

        search_view_id = ref('product.product_search_form_view')
        graph_view_id = ref('product_margin.view_product_margin_graph')
        form_view_id = ref('product_margin.view_product_margin_form')
        tree_view_id = ref('product_margin.view_product_margin_tree')

        context.update(invoice_state=self.invoice_state)

        if self.from_date:
            context.update(date_from=self.from_date)

        if self.to_date:
            context.update(date_to=self.to_date)

        self.env['account.move.line'].flush_model(['product_id'])
        self.env['account.move'].flush_model(['state', 'payment_state', 'invoice_date', 'company_id'])
        sqlstr = """
                SELECT
                    DISTINCT(aml.product_id)
                FROM account_move_line aml
                LEFT JOIN account_move am ON (aml.move_id = am.id)
                WHERE am.state IN %s
                AND am.payment_state IN %s
                AND am.move_type IN ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')
                AND am.invoice_date BETWEEN %s AND  %s
                AND am.company_id = %s
                AND aml.display_type = 'product'
                """
        states = ()
        payment_states = ()
        if self.invoice_state == 'paid':
            states = ('posted',)
            payment_states = ('in_payment', 'paid', 'reversed')
        elif self.invoice_state == 'open_paid':
            states = ('posted',)
            payment_states = ('not_paid', 'in_payment', 'paid', 'reversed', 'partial')
        elif self.invoice_state == 'draft_open_paid':
            states = ('posted', 'draft')
            payment_states = ('not_paid', 'in_payment', 'paid', 'reversed', 'partial')
        if "force_company" in self.env.context:
            company_id = self.env.context['force_company']
        else:
            company_id = self.env.company.id
        self.env.cr.execute(sqlstr, (states, payment_states, self.from_date, self.to_date, company_id))
        product_ids = [p[0] for p in self.env.cr.fetchall()]
        views = [
            (tree_view_id, 'tree'),
            (form_view_id, 'form'),
            (graph_view_id, 'graph')
        ]
        return {
            'name': _('Product Margins'),
            'context': context,
            "view_mode": 'tree,form,graph',
            'res_model': 'product.product',
            'type': 'ir.actions.act_window',
            'views': views,
            'view_id': False,
            'search_view_id': [search_view_id],
            'domain': [('id', 'in', product_ids)],
        }
