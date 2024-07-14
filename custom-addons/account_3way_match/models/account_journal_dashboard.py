# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def open_action(self):
        action = super(AccountJournal, self).open_action()
        view = self.env.ref('account.action_move_in_invoice_type')
        if view and action.get("id") == view.id:
            account_purchase_filter = self.env.ref('account_3way_match.account_invoice_filter_inherit_account_3way_match', False)
            action['search_view_id'] = account_purchase_filter and [account_purchase_filter.id, account_purchase_filter.name] or False
        return action

    def _patch_dashboard_query_3way_match(self, query):
        query.add_where("("
            "account_move.move_type NOT IN %s "
            "OR account_move.release_to_pay = 'yes' "
            "OR account_move.invoice_date_due < %s"
        ")", [
            tuple(self.env['account.move'].get_purchase_types(include_receipts=True)),
            fields.Date.context_today(self),
        ])

    def _get_open_bills_to_pay_query(self):
        query = super()._get_open_bills_to_pay_query()
        self._patch_dashboard_query_3way_match(query)
        return query

    def _get_draft_bills_query(self):
        query = super()._get_draft_bills_query()
        self._patch_dashboard_query_3way_match(query)
        return query

    def _get_late_bills_query(self):
        query = super()._get_late_bills_query()
        self._patch_dashboard_query_3way_match(query)
        return query
