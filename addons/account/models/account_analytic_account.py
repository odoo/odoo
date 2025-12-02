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
        data = self.env['account.move.line']._read_group(
            [
                ('parent_state', '=', 'posted'),
                ('move_id.move_type', 'in', sale_types),
                ('analytic_distribution', 'in', self.ids),
            ],
            ['analytic_distribution'],
            ['__count'],
        )
        data = {int(account_id): move_count for account_id, move_count in data}
        for account in self:
            account.invoice_count = data.get(account.id, 0)

    @api.depends('line_ids')
    def _compute_vendor_bill_count(self):
        purchase_types = self.env['account.move'].get_purchase_types(include_receipts=True)
        data = self.env['account.move.line']._read_group(
            [
                ('parent_state', '=', 'posted'),
                ('move_id.move_type', 'in', purchase_types),
                ('analytic_distribution', 'in', self.ids),
            ],
            ['analytic_distribution'],
            ['__count'],
        )
        data = {int(account_id): move_count for account_id, move_count in data}
        for account in self:
            account.vendor_bill_count = data.get(account.id, 0)

    def action_view_invoice(self):
        self.ensure_one()
        account_move_lines = self.env['account.move.line'].search_fetch([
            ('move_id.move_type', 'in', self.env['account.move'].get_sale_types()),
            ('analytic_distribution', 'in', self.ids),
        ], ['move_id'])
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('id', 'in', account_move_lines.move_id.ids)],
            "context": {"create": False, 'default_move_type': 'out_invoice'},
            "name": _("Customer Invoices"),
            'view_mode': 'list,form',
        }

    def action_view_vendor_bill(self):
        self.ensure_one()
        account_move_lines = self.env['account.move.line'].search_fetch([
            ('move_id.move_type', 'in', self.env['account.move'].get_purchase_types()),
            ('analytic_distribution', 'in', self.ids),
        ], ['move_id'])
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('id', 'in', account_move_lines.move_id.ids)],
            "context": {"create": False, 'default_move_type': 'in_invoice'},
            "name": _("Vendor Bills"),
            'view_mode': 'list,form',
        }
