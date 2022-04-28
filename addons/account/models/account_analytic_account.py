# -*- coding: utf-8 -*-

from odoo import api, fields, models


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
        domain = [
            ('move_line_id.move_id.move_type', 'in', sale_types),
            ('account_id', 'in', self.ids)
        ]
        groups = self.env['account.analytic.line']._read_group(domain, ['move_line_id.move_id:count_distinct'], ['account_id'])
        moves_count_mapping = dict((g['account_id'][0], g['account_id_count']) for g in groups)
        for account in self:
            account.invoice_count = moves_count_mapping.get(account.id, 0)

    @api.depends('line_ids')
    def _compute_vendor_bill_count(self):
        purchase_types = self.env['account.move'].get_purchase_types(include_receipts=True)
        domain = [
            ('move_line_id.move_id.move_type', 'in', purchase_types),
            ('account_id', 'in', self.ids)
        ]
        groups = self.env['account.analytic.line']._read_group(domain, ['move_line_id.move_id:count_distinct'], ['account_id'])
        moves_count_mapping = dict((g['account_id'][0], g['account_id_count']) for g in groups)
        for account in self:
            account.vendor_bill_count = moves_count_mapping.get(account.id, 0)

    def action_view_invoice(self):
        self.ensure_one()
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('line_ids.analytic_distribution_stored_char', '=ilike', f'%"{self.id}":%'), ('move_type', 'in', self.env['account.move'].get_sale_types())],
            "context": {"create": False},
            "name": "Customer Invoices",
            'view_mode': 'tree,form',
        }
        return result

    def action_view_vendor_bill(self):
        self.ensure_one()
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('line_ids.analytic_distribution_stored_char', '=ilike', f'%"{self.id}":%'), ('move_type', 'in', self.env['account.move'].get_purchase_types())],
            "context": {"create": False},
            "name": "Vendor Bills",
            'view_mode': 'tree,form',
        }
        return result
