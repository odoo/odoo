# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
import json

from odoo import _, api, fields, models, Command
from odoo.addons.web.controllers.utils import clean_action


class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'

    selected_batch_payment_ids = fields.Many2many(
        comodel_name='account.batch.payment',
        compute='_compute_selected_batch_payment_ids',
    )

    def _fetch_available_amls_in_batch_payments(self, batch_payments=None):
        self.ensure_one()
        st_line = self.st_line_id

        amls_domain = st_line._get_default_amls_matching_domain()
        query = self.env['account.move.line']._where_calc(amls_domain)
        tables, where_clause, where_params = query.get_sql()

        if batch_payments:
            where_clause += " AND pay.batch_payment_id IN %s"
            where_params.append(tuple(batch_payments.ids))

        self._cr.execute(
            f'''
                SELECT
                    pay.batch_payment_id,
                    ARRAY_AGG(account_move_line.id) AS aml_ids
                FROM {tables}
                JOIN account_payment pay ON pay.id = account_move_line.payment_id
                JOIN account_batch_payment batch ON batch.id = pay.batch_payment_id
                WHERE {where_clause}
                    AND pay.batch_payment_id IS NOT NULL
                    AND batch.state != 'reconciled'
                GROUP BY pay.batch_payment_id
            ''',
            where_params,
        )
        return {r[0]: r[1] for r in self._cr.fetchall()}

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('company_id', 'line_ids.source_batch_payment_id')
    def _compute_selected_batch_payment_ids(self):
        for wizard in self:
            batch_payment_x_amls = defaultdict(set)
            for line in wizard.line_ids:
                if line.source_batch_payment_id:
                    batch_payment_x_amls[line.source_batch_payment_id].add(line.source_aml_id.id)

            if batch_payment_x_amls:
                batch_payments = wizard.line_ids.source_batch_payment_id
                available_amls_in_batch_payments = wizard._fetch_available_amls_in_batch_payments(batch_payments=batch_payments)
                selected_batch_payment_ids = [
                    x.id
                    for x in batch_payments
                    if batch_payment_x_amls[x] == set(available_amls_in_batch_payments.get(x.id, []))
                ]
            else:
                selected_batch_payment_ids = []

            wizard.selected_batch_payment_ids = [Command.set(selected_batch_payment_ids)]

    # -------------------------------------------------------------------------
    # HELPERS RPC
    # -------------------------------------------------------------------------

    def _prepare_embedded_views_data(self):
        # EXTENDS 'account_accountant'
        results = super()._prepare_embedded_views_data()
        st_line = self.st_line_id

        context = {
            'search_view_ref': 'account_accountant_batch_payment.view_account_batch_payment_search_bank_rec_widget',
            'tree_view_ref': 'account_accountant_batch_payment.view_account_batch_payment_list_bank_rec_widget',
        }

        dynamic_filters = []

        # == Dynamic filter for the same journal ==
        journal = st_line.journal_id
        dynamic_filters.append({
            'name': 'same_journal',
            'description': journal.display_name,
            'domain': [('journal_id', '=', journal.id)],
        })
        context['search_default_same_journal'] = True

        # == Dynamic Currency filter ==
        if self.transaction_currency_id != self.company_currency_id:
            context['search_default_currency_id'] = self.transaction_currency_id.id

        # Stringify the domain.
        for dynamic_filter in dynamic_filters:
            dynamic_filter['domain'] = str(dynamic_filter['domain'])

        # Collect the available batch payments.
        available_amls_in_batch_payments = self._fetch_available_amls_in_batch_payments()

        results['batch_payments'] = {
            'domain': [('id', 'in', list(available_amls_in_batch_payments.keys()))],
            'dynamic_filters': dynamic_filters,
            'context': context,
        }
        return results

    # -------------------------------------------------------------------------
    # LINES METHODS
    # -------------------------------------------------------------------------

    def _lines_prepare_new_aml_line(self, aml, **kwargs):
        # EXTENDS account_accountant
        return super()._lines_prepare_new_aml_line(
            aml,
            source_batch_payment_id=aml.payment_id.batch_payment_id,
            **kwargs,
        )

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def _action_add_new_batch_payments(self, batch_payments):
        self.ensure_one()
        amls = self.env['account.move.line']
        amls_domain = self.st_line_id._get_default_amls_matching_domain()
        mounted_payments = set(self.line_ids.filtered(lambda x: x.flag == 'new_aml').source_aml_id.payment_id)
        for batch in batch_payments:
            for payment in batch.payment_ids:
                if payment not in mounted_payments:
                    liquidity_lines, _counterpart_lines, _writeoff_lines = payment._seek_for_lines()
                    amls |= liquidity_lines.filtered_domain(amls_domain)
        self._action_add_new_amls(amls, allow_partial=False)

    def _js_action_add_new_batch_payment(self, batch_payment_id):
        self.ensure_one()
        batch_payment = self.env['account.batch.payment'].browse(batch_payment_id)
        self._action_add_new_batch_payments(batch_payment)

    def _action_remove_new_batch_payments(self, batch_payments):
        self.ensure_one()
        lines = self.line_ids.filtered(lambda x: x.flag == 'new_aml' and x.source_batch_payment_id in batch_payments)
        self._action_remove_lines(lines)

    def _js_action_remove_new_batch_payment(self, batch_payment_id):
        self.ensure_one()
        batch_payment = self.env['account.batch.payment'].browse(batch_payment_id)
        self._action_remove_new_batch_payments(batch_payment)

    def _js_action_validate(self):
        # EXTENDS account_accountant
        # Open the 'account.batch.payment.rejection' wizard if needed.

        payments_with_batch = self.line_ids\
            .filtered(lambda x: x.flag == 'new_aml' and x.source_batch_payment_id)\
            .source_aml_id.payment_id
        if len(payments_with_batch) > 1 and self.env['account.batch.payment.rejection']._fetch_rejected_payment_ids(payments_with_batch):
            self.return_todo_command = {
                'open_batch_rejection_wizard': clean_action(
                    {
                        'name': _("Batch Payment"),
                        'type': 'ir.actions.act_window',
                        'res_model': 'account.batch.payment.rejection',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_in_reconcile_payment_ids': [Command.set(payments_with_batch.ids)],
                        },
                    },
                    self.env,
                ),
            }
            return
        super()._js_action_validate()

    def _js_action_validate_no_batch_payment_check(self):
        super()._js_action_validate()
