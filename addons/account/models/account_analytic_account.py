# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools import SQL


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

    debit = fields.Monetary(groups='account.group_account_readonly')
    credit = fields.Monetary(groups='account.group_account_readonly')

    @api.depends('line_ids')
    def _compute_invoice_count(self):
        sale_types = self.env['account.move'].get_sale_types(include_receipts=True)

        query = self.env['account.move.line']._search([
            ('parent_state', '=', 'posted'),
            ('move_id.move_type', 'in', sale_types),
        ])
        query.add_where(
            SQL(
                "%s && %s",
                [str(account_id) for account_id in self.ids],
                self.env['account.move.line']._query_analytic_accounts(),
            )
        )

        query_string, query_param = query.select(
            r"""DISTINCT move_id, (regexp_matches(jsonb_object_keys(account_move_line.analytic_distribution), '\d+', 'g'))[1]::int as account_id"""
        )
        query_string = f"""
            SELECT account_id, count(move_id) FROM
            ({query_string}) distribution
            GROUP BY account_id
        """

        self._cr.execute(query_string, query_param)
        data = {res['account_id']: res['count'] for res in self._cr.dictfetchall()}
        for account in self:
            account.invoice_count = data.get(account.id, 0)

    @api.depends('line_ids')
    def _compute_vendor_bill_count(self):
        purchase_types = self.env['account.move'].get_purchase_types(include_receipts=True)

        query = self.env['account.move.line']._search([
            ('parent_state', '=', 'posted'),
            ('move_id.move_type', 'in', purchase_types),
        ])
        query.add_where(
            SQL(
                "%s && %s",
                [str(account_id) for account_id in self.ids],
                self.env['account.move.line']._query_analytic_accounts(),
            )
        )

        query_string, query_param = query.select(
            r"""DISTINCT move_id, (regexp_matches(jsonb_object_keys(account_move_line.analytic_distribution), '\d+', 'g'))[1]::int as account_id"""
        )
        query_string = f"""
            SELECT account_id, count(move_id) FROM
            ({query_string}) distribution
            GROUP BY account_id
        """

        self._cr.execute(query_string, query_param)
        data = {res['account_id']: res['count'] for res in self._cr.dictfetchall()}
        for account in self:
            account.vendor_bill_count = data.get(account.id, 0)

    def action_view_invoice(self):
        self.ensure_one()
        query = self.env['account.move.line']._search([('move_id.move_type', 'in', self.env['account.move'].get_sale_types())])
        query.add_where(
            SQL(
                "%s && %s",
                [str(self.id)],
                self.env['account.move.line']._query_analytic_accounts(),
            )
        )
        query_string, query_param = query.select('DISTINCT account_move_line.move_id')
        self._cr.execute(query_string, query_param)
        move_ids = [line.get('move_id') for line in self._cr.dictfetchall()]
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('id', 'in', move_ids)],
            "context": {"create": False, 'default_move_type': 'out_invoice'},
            "name": _("Customer Invoices"),
            'view_mode': 'tree,form',
        }
        return result

    def action_view_vendor_bill(self):
        self.ensure_one()
        query = self.env['account.move.line']._search([('move_id.move_type', 'in', self.env['account.move'].get_purchase_types())])
        query.add_where(
            SQL(
                "%s && %s",
                [str(self.id)],
                self.env['account.move.line']._query_analytic_accounts(),
            )
        )
        query_string, query_param = query.select('DISTINCT account_move_line.move_id')
        self._cr.execute(query_string, query_param)
        move_ids = [line.get('move_id') for line in self._cr.dictfetchall()]
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('id', 'in', move_ids)],
            "context": {"create": False, 'default_move_type': 'in_invoice'},
            "name": _("Vendor Bills"),
            'view_mode': 'tree,form',
        }
        return result
