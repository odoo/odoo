# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    invoice_count = fields.Integer(
        "Invoice Count",
        compute='_compute_invoice_count',
    )
    vendor_bill_count = fields.Integer(
        "Vendor Bill Count",
        compute='_compute_vendor_bill_count',
    )

    @api.depends('line_ids')
    def _compute_invoice_count(self):
        sale_types = self.env['account.move'].get_sale_types(include_receipts=True)

        query = self.env['account.move.line']._search([
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', 'in', sale_types),
        ])
        query.add_where(
            'account_move_line.analytic_distribution ?| array[%s]',
            [str(account_id) for account_id in self.ids],
        )

        query.order = None
        query_string, query_param = query.select(
            'jsonb_object_keys(account_move_line.analytic_distribution) as account_id',
            'COUNT(DISTINCT(move_id)) as move_count',
        )
        query_string = f"{query_string} GROUP BY jsonb_object_keys(account_move_line.analytic_distribution)"

        self._cr.execute(query_string, query_param)
        data = {int(record.get('account_id')): record.get('move_count') for record in self._cr.dictfetchall()}
        for account in self:
            account.invoice_count = data.get(account.id, 0)

    @api.depends('line_ids')
    def _compute_vendor_bill_count(self):
        purchase_types = self.env['account.move'].get_purchase_types(include_receipts=True)

        query = self.env['account.move.line']._search([
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', 'in', purchase_types),
        ])
        query.add_where(
            'account_move_line.analytic_distribution ?| array[%s]',
            [str(account_id) for account_id in self.ids],
        )

        query.order = None
        query_string, query_param = query.select(
            'jsonb_object_keys(account_move_line.analytic_distribution) as account_id',
            'COUNT(DISTINCT(move_id)) as move_count',
        )
        query_string = f"{query_string} GROUP BY jsonb_object_keys(account_move_line.analytic_distribution)"

        self._cr.execute(query_string, query_param)
        data = {int(record.get('account_id')): record.get('move_count') for record in self._cr.dictfetchall()}
        for account in self:
            account.vendor_bill_count = data.get(account.id, 0)

    def action_view_invoice(self):
        self.ensure_one()
        query = self.env['account.move.line']._search([('move_id.move_type', 'in', self.env['account.move'].get_sale_types())])
        query.order = None
        query.add_where('analytic_distribution ? %s', [str(self.id)])
        query_string, query_param = query.select('DISTINCT move_id')
        self._cr.execute(query_string, query_param)
        move_ids = [line.get('move_id') for line in self._cr.dictfetchall()]
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('id', 'in', move_ids)],
            "context": {"create": False},
            "name": _("Customer Invoices"),
            'view_mode': 'tree,form',
        }
        return result

    def action_view_vendor_bill(self):
        self.ensure_one()
        query = self.env['account.move.line']._search([('move_id.move_type', 'in', self.env['account.move'].get_purchase_types())])
        query.order = None
        query.add_where('analytic_distribution ? %s', [str(self.id)])
        query_string, query_param = query.select('DISTINCT move_id')
        self._cr.execute(query_string, query_param)
        move_ids = [line.get('move_id') for line in self._cr.dictfetchall()]
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('id', 'in', move_ids)],
            "context": {"create": False},
            "name": _("Vendor Bills"),
            'view_mode': 'tree,form',
        }
        return result
