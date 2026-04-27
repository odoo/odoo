# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.osv import expression
from odoo.tools import SQL


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def open_action(self):
        action = super(AccountJournal, self).open_action()
        view = self.env.ref('account.action_move_in_invoice_type')
        if view and action.get("id") == view.id:
            action['context']['search_default_in_invoice'] = 0
            account_purchase_filter = self.env.ref('account_3way_match.account_invoice_filter_inherit_account_3way_match', False)
            action['search_view_id'] = account_purchase_filter and [account_purchase_filter.id, account_purchase_filter.name] or False
        return action

    def _get_open_sale_purchase_query(self, journal_type):
        # OVERRIDE
        assert journal_type in ('sale', 'purchase')
        query = self.env['account.move']._where_calc([
            *self.env['account.move']._check_company_domain(self.env.companies),
            ('journal_id', 'in', self.ids),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('move_type', 'in', ('out_invoice', 'out_refund', 'out_receipt') if journal_type == 'sale' else ('in_invoice', 'in_refund', 'in_receipt')),
            ('state', '=', 'posted'),
        ])

        selects = [
            SQL("journal_id"),
            SQL("company_id"),
            SQL("currency_id AS currency"),
            SQL("invoice_date_due < %s AS late", fields.Date.context_today(self)),
            SQL("SUM(amount_residual_signed) AS amount_total_company"),
            SQL("SUM((CASE WHEN move_type = 'in_invoice' THEN -1 ELSE 1 END) * amount_residual) AS amount_total"),
            SQL("COUNT(*)"),
            SQL("release_to_pay IN ('yes', 'exception') AS to_pay")
        ]

        return query, selects

    def _get_draft_sales_purchases_query(self):
        # OVERRIDE
        domain_sale = [
            ('journal_id', 'in', self.filtered(lambda j: j.type == 'sale').ids),
            ('move_type', 'in', self.env['account.move'].get_sale_types(include_receipts=True))
        ]

        domain_purchase = [
            ('journal_id', 'in', self.filtered(lambda j: j.type == 'purchase').ids),
            ('move_type', 'in', self.env['account.move'].get_purchase_types(include_receipts=False)),
            '|',
            ('invoice_date_due', '<', fields.Date.today()),
            ('release_to_pay', '=', 'yes')
        ]
        domain = expression.AND([
            [('state', '=', 'draft'), ('payment_state', 'in', ('not_paid', 'partial'))],
            expression.OR([domain_sale, domain_purchase])
        ])
        return self.env['account.move']._where_calc([
            *self.env['account.move']._check_company_domain(self.env.companies),
            *domain
        ])
