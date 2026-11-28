# -*- coding: utf-8 -*-
"""Direct-method Cash Flow Statement (Enterprise account.cash.flow.report.handler).

Enterprise menu opens the Indirect variant by default; that layout depends on
account tags (adj_*, wcap_*, …) that Community CoA does not ship. The Direct
method is the root Cash Flow Statement engine and is portable with the shared
operating / investing / financing tags. Layout, dispatch, and liquidity /
reconciled-move math mirror Enterprise.
"""
from odoo import _, api, fields, models
from odoo.tools import SQL


class FsCashFlow(models.AbstractModel):
    _name = 'fs.cash.flow'
    _description = 'Cash Flow Statement (Direct Method)'

    # -------------------------------------------------------------------------
    # Public API (used by fs.report.engine)
    # -------------------------------------------------------------------------

    @api.model
    def get_report_data(self, report, options):
        self = self.with_context(allowed_company_ids=options['company_ids'])
        # Raw SQL reads parent_state; flush so just-posted moves are visible.
        self.env.flush_all()
        layout_data = self._get_layout_data()
        report_data = self._compute_report_data(options, layout_data)
        n = len(options['columns'])
        out = []
        unfold_all = bool(options.get('unfold_all'))

        for layout_line_id, layout_line_data in layout_data.items():
            balances = (
                report_data.get(layout_line_id, {}).get('balance', {})
                if layout_line_id in report_data else {}
            )
            columns = [balances.get(i, 0.0) for i in range(n)]
            accounts = []
            aml_map = report_data.get(layout_line_id, {}).get('aml_groupby_account') or {}
            if aml_map:
                with_code = [a for a in aml_map.values() if a.get('account_code') is not None]
                without_code = [a for a in aml_map.values() if a.get('account_code') is None]
                for aml in sorted(with_code, key=lambda x: x['account_code'] or '') + without_code:
                    accounts.append({
                        'id': aml['account_id'],
                        'name': (
                            f"{aml['account_code']} {aml['account_name']}"
                            if aml.get('account_code') else aml['account_name']
                        ),
                        'code': aml.get('account_code') or '',
                        'columns': [aml['balance'].get(i, 0.0) for i in range(n)],
                        'caret_options': 'account.account',
                    })
            unfoldable = bool(accounts)
            default_unfolded = bool(layout_line_data.get('unfolded'))
            out.append({
                'id': layout_line_id,
                'code': layout_line_id,
                'name': layout_line_data['name'],
                'parent_id': layout_line_data.get('parent_line_id') or False,
                'level': layout_line_data['level'],
                'formula_type': 'cash_flow',
                'account_types': '',
                'sign': 1,
                'unfoldable': unfoldable,
                'default_unfolded': default_unfolded or unfold_all,
                'columns': columns,
                'hide_if_zero': False,
                'horizontal_split_side': False,
                'action_id': False,
                'auditable': unfoldable,
                'green_on_positive': False,
                'css_class': layout_line_data.get('class', ''),
                'accounts': accounts,
            })

        unexplained = self._unexplained_difference_columns(options, report_data)
        if unexplained is not None:
            out.append({
                'id': 'unexplained_difference',
                'code': 'unexplained_difference',
                'name': _('Unexplained Difference'),
                'parent_id': False,
                'level': 1,
                'formula_type': 'cash_flow',
                'account_types': '',
                'sign': 1,
                'unfoldable': False,
                'default_unfolded': False,
                'columns': unexplained,
                'hide_if_zero': False,
                'horizontal_split_side': False,
                'action_id': False,
                'auditable': False,
                'green_on_positive': False,
                'css_class': '',
                'accounts': [],
            })

        return {
            'lines': out,
            'has_unposted': self.env['fs.report.engine']._has_unposted_moves(options),
        }

    @api.model
    def get_account_lines(self, line_id, options):
        data = self.get_report_data(self.env['fs.report'], options)
        for row in data['lines']:
            if row['id'] == line_id:
                return row.get('accounts') or []
        return []

    # -------------------------------------------------------------------------
    # Layout (Enterprise _get_layout_data)
    # -------------------------------------------------------------------------

    @api.model
    def _get_layout_data(self):
        return {
            'opening_balance': {
                'name': _('Cash and cash equivalents, beginning of period'),
                'level': 0,
            },
            'net_increase': {
                'name': _('Net increase in cash and cash equivalents'),
                'level': 0,
                'unfolded': True,
            },
            'operating_activities': {
                'name': _('Cash flows from operating activities'),
                'level': 2,
                'parent_line_id': 'net_increase',
                'class': 'fw-bold',
                'unfolded': True,
            },
            'advance_payments_customer': {
                'name': _('Advance Payments received from customers'),
                'level': 4,
                'parent_line_id': 'operating_activities',
            },
            'received_operating_activities': {
                'name': _('Cash received from operating activities'),
                'level': 4,
                'parent_line_id': 'operating_activities',
            },
            'advance_payments_suppliers': {
                'name': _('Advance payments made to suppliers'),
                'level': 4,
                'parent_line_id': 'operating_activities',
            },
            'paid_operating_activities': {
                'name': _('Cash paid for operating activities'),
                'level': 4,
                'parent_line_id': 'operating_activities',
            },
            'investing_activities': {
                'name': _('Cash flows from investing & extraordinary activities'),
                'level': 2,
                'parent_line_id': 'net_increase',
                'class': 'fw-bold',
                'unfolded': True,
            },
            'investing_activities_cash_in': {
                'name': _('Cash in'),
                'level': 4,
                'parent_line_id': 'investing_activities',
            },
            'investing_activities_cash_out': {
                'name': _('Cash out'),
                'level': 4,
                'parent_line_id': 'investing_activities',
            },
            'financing_activities': {
                'name': _('Cash flows from financing activities'),
                'level': 2,
                'parent_line_id': 'net_increase',
                'class': 'fw-bold',
                'unfolded': True,
            },
            'financing_activities_cash_in': {
                'name': _('Cash in'),
                'level': 4,
                'parent_line_id': 'financing_activities',
            },
            'financing_activities_cash_out': {
                'name': _('Cash out'),
                'level': 4,
                'parent_line_id': 'financing_activities',
            },
            'unclassified_activities': {
                'name': _('Cash flows from unclassified activities'),
                'level': 2,
                'parent_line_id': 'net_increase',
                'class': 'fw-bold',
                'unfolded': True,
            },
            'unclassified_activities_cash_in': {
                'name': _('Cash in'),
                'level': 4,
                'parent_line_id': 'unclassified_activities',
            },
            'unclassified_activities_cash_out': {
                'name': _('Cash out'),
                'level': 4,
                'parent_line_id': 'unclassified_activities',
            },
            'closing_balance': {
                'name': _('Cash and cash equivalents, closing balance'),
                'level': 0,
            },
        }

    # -------------------------------------------------------------------------
    # Computation
    # -------------------------------------------------------------------------

    @api.model
    def _compute_report_data(self, options, layout_data):
        report_data = {}
        payment_account_ids = self._get_payment_account_ids(options)
        if not payment_account_ids:
            return report_data

        for aml_data in self._compute_liquidity_balance(
                options, payment_account_ids, 'to_beginning_of_period'):
            self._add_report_data('opening_balance', aml_data, layout_data, report_data)
            self._add_report_data('closing_balance', aml_data, layout_data, report_data)

        for aml_data in self._compute_liquidity_balance(
                options, payment_account_ids, 'strict_range'):
            self._add_report_data('closing_balance', aml_data, layout_data, report_data)

        tags_ids = self._get_tags_ids()
        cashflow_tag_ids = list(tags_ids.values())

        for aml_groupby_account in self._get_liquidity_moves(
                options, payment_account_ids, cashflow_tag_ids):
            for aml_data in aml_groupby_account.values():
                self._dispatch_aml_data(tags_ids, aml_data, layout_data, report_data)

        for aml_groupby_account in self._get_reconciled_moves(
                options, payment_account_ids, cashflow_tag_ids):
            for aml_data in aml_groupby_account.values():
                self._dispatch_aml_data(tags_ids, aml_data, layout_data, report_data)

        return report_data

    @api.model
    def _get_tags_ids(self):
        return {
            'operating': self.env.ref('account.account_tag_operating').id,
            'investing': self.env.ref('account.account_tag_investing').id,
            'financing': self.env.ref('account.account_tag_financing').id,
        }

    @api.model
    def _dispatch_aml_data(self, tags_ids, aml_data, layout_data, report_data):
        if aml_data['account_account_type'] == 'asset_receivable':
            self._add_report_data('advance_payments_customer', aml_data, layout_data, report_data)
        elif aml_data['account_account_type'] == 'liability_payable':
            self._add_report_data('advance_payments_suppliers', aml_data, layout_data, report_data)
        elif aml_data['balance'] < 0:
            if aml_data['account_tag_id'] == tags_ids['operating']:
                self._add_report_data('paid_operating_activities', aml_data, layout_data, report_data)
            elif aml_data['account_tag_id'] == tags_ids['investing']:
                self._add_report_data('investing_activities_cash_out', aml_data, layout_data, report_data)
            elif aml_data['account_tag_id'] == tags_ids['financing']:
                self._add_report_data('financing_activities_cash_out', aml_data, layout_data, report_data)
            else:
                self._add_report_data('unclassified_activities_cash_out', aml_data, layout_data, report_data)
        elif aml_data['balance'] > 0:
            if aml_data['account_tag_id'] == tags_ids['operating']:
                self._add_report_data('received_operating_activities', aml_data, layout_data, report_data)
            elif aml_data['account_tag_id'] == tags_ids['investing']:
                self._add_report_data('investing_activities_cash_in', aml_data, layout_data, report_data)
            elif aml_data['account_tag_id'] == tags_ids['financing']:
                self._add_report_data('financing_activities_cash_in', aml_data, layout_data, report_data)
            else:
                self._add_report_data('unclassified_activities_cash_in', aml_data, layout_data, report_data)

    @api.model
    def _add_report_data(self, layout_line_id, aml_data, layout_data, report_data):
        def update_parent(line_id, col_idx, balance):
            parent = layout_data[line_id].get('parent_line_id')
            if not parent:
                return
            report_data.setdefault(parent, {'balance': {}})
            report_data[parent]['balance'].setdefault(col_idx, 0.0)
            report_data[parent]['balance'][col_idx] += balance
            update_parent(parent, col_idx, balance)

        col_idx = aml_data['column_group_index']
        balance = aml_data['balance']
        company = self.env.company
        if company.currency_id.is_zero(balance):
            return

        report_data.setdefault(layout_line_id, {
            'balance': {},
            'aml_groupby_account': {},
        })
        report_data[layout_line_id]['aml_groupby_account'].setdefault(aml_data['account_id'], {
            'parent_line_id': layout_line_id,
            'account_id': aml_data['account_id'],
            'account_code': aml_data['account_code'],
            'account_name': aml_data['account_name'],
            'account_tag_id': aml_data.get('account_tag_id'),
            'level': layout_data[layout_line_id]['level'] + 1,
            'balance': {},
        })
        report_data[layout_line_id]['balance'].setdefault(col_idx, 0.0)
        report_data[layout_line_id]['balance'][col_idx] += balance
        report_data[layout_line_id]['aml_groupby_account'][aml_data['account_id']]['balance'].setdefault(col_idx, 0.0)
        report_data[layout_line_id]['aml_groupby_account'][aml_data['account_id']]['balance'][col_idx] += balance
        update_parent(layout_line_id, col_idx, balance)

    @api.model
    def _unexplained_difference_columns(self, options, report_data):
        currency = self.env.company.currency_id
        columns = []
        has_diff = False
        for i, _col in enumerate(options['columns']):
            opening = report_data.get('opening_balance', {}).get('balance', {}).get(i, 0.0)
            closing = report_data.get('closing_balance', {}).get('balance', {}).get(i, 0.0)
            net = report_data.get('net_increase', {}).get('balance', {}).get(i, 0.0)
            balance = closing - opening - net
            if not currency.is_zero(balance):
                has_diff = True
            columns.append(balance)
        return columns if has_diff else None

    # -------------------------------------------------------------------------
    # Domains / state filters
    # -------------------------------------------------------------------------

    @api.model
    def _state_sql(self, options):
        if options.get('target_move', 'posted') == 'posted':
            return SQL("account_move_line.parent_state = 'posted'")
        return SQL("account_move_line.parent_state != 'cancel'")

    @api.model
    def _company_sql(self, options):
        return SQL(
            "account_move_line.company_id IN %s",
            tuple(options['company_ids']),
        )

    # -------------------------------------------------------------------------
    # Payment / liquidity accounts
    # -------------------------------------------------------------------------

    @api.model
    def _get_payment_account_ids(self, options):
        """Liquidity accounts for Direct CF — Enterprise `_get_account_ids` + CoA outstanding.

        Enterprise collects journal default (cash/credit card) and payment-method
        outstanding accounts. Community charts often leave method-line
        ``payment_account_id`` empty and resolve outstanding via chart template
        refs; include those so payments are visible before bank reconciliation.
        """
        selected_journal_ids = options.get('journal_ids') or []
        Journal = self.env['account.journal']
        if selected_journal_ids:
            journals = Journal.browse(selected_journal_ids)
        else:
            journals = Journal.search([
                ('company_id', 'in', options['company_ids']),
                ('type', 'in', ('bank', 'cash', 'general')),
            ])
        account_ids = set()
        for journal in journals:
            if journal.default_account_id and journal.default_account_id.account_type in (
                    'asset_cash', 'liability_credit_card'):
                account_ids.add(journal.default_account_id.id)
            for line in journal.inbound_payment_method_line_ids | journal.outbound_payment_method_line_ids:
                if line.payment_account_id:
                    account_ids.add(line.payment_account_id.id)

        # Chart-template outstanding receipts/payments (Odoo 20 payment fallback).
        companies = self.env['res.company'].browse(options['company_ids'])
        for company in companies:
            chart = self.env['account.chart.template'].with_company(company)
            for xmlid in (
                    'account_journal_payment_debit_account_id',
                    'account_journal_payment_credit_account_id',
            ):
                account = chart.ref(xmlid, raise_if_not_found=False)
                if account:
                    account_ids.add(account.id)
            if company.transfer_account_id:
                account_ids.add(company.transfer_account_id.id)

        return tuple(account_ids)

    # -------------------------------------------------------------------------
    # Liquidity balances (opening / period)
    # -------------------------------------------------------------------------

    @api.model
    def _account_meta(self, account_ids, cashflow_tag_ids=None):
        """Resolve code/name/type/tag without SQL on translated/computed columns."""
        tag_set = set(cashflow_tag_ids or [])
        meta = {}
        for account in self.env['account.account'].browse(account_ids):
            tag_id = next((t.id for t in account.tag_ids if t.id in tag_set), None)
            meta[account.id] = {
                'account_code': account.code,
                'account_name': account.name,
                'account_account_type': account.account_type,
                'account_tag_id': tag_id,
            }
        return meta

    @api.model
    def _compute_liquidity_balance(self, options, payment_account_ids, date_scope):
        rows = []
        for col_idx, col in enumerate(options['columns']):
            date_from = fields.Date.to_date(col['date_from'])
            date_to = fields.Date.to_date(col['date_to'])
            if date_scope == 'to_beginning_of_period':
                date_domain = SQL("account_move_line.date < %(date_from)s", date_from=date_from)
            else:
                date_domain = SQL(
                    "account_move_line.date >= %(date_from)s AND account_move_line.date <= %(date_to)s",
                    date_from=date_from,
                    date_to=date_to,
                )
            self.env.cr.execute(SQL(
                """
                SELECT
                    %(col_idx)s AS column_group_index,
                    account_move_line.account_id,
                    SUM(account_move_line.balance) AS balance
                FROM account_move_line
                WHERE %(company)s
                  AND %(state)s
                  AND %(date_domain)s
                  AND account_move_line.account_id IN %(payment_account_ids)s
                GROUP BY account_move_line.account_id
                """,
                col_idx=col_idx,
                company=self._company_sql(options),
                state=self._state_sql(options),
                date_domain=date_domain,
                payment_account_ids=payment_account_ids,
            ))
            raw = self.env.cr.dictfetchall()
            meta = self._account_meta([r['account_id'] for r in raw])
            for row in raw:
                row.update(meta.get(row['account_id'], {
                    'account_code': '',
                    'account_name': '',
                    'account_account_type': False,
                    'account_tag_id': None,
                }))
                rows.append(row)
        return rows

    # -------------------------------------------------------------------------
    # Liquidity moves (not-reconciled portion)
    # -------------------------------------------------------------------------

    @api.model
    def _payment_move_ids(self, options, payment_account_ids, date_from, date_to):
        self.env.cr.execute(SQL(
            """
            SELECT DISTINCT account_move_line.move_id
            FROM account_move_line
            WHERE %(company)s
              AND %(state)s
              AND account_move_line.date >= %(date_from)s
              AND account_move_line.date <= %(date_to)s
              AND account_move_line.account_id IN %(payment_account_ids)s
            """,
            company=self._company_sql(options),
            state=self._state_sql(options),
            date_from=date_from,
            date_to=date_to,
            payment_account_ids=payment_account_ids,
        ))
        return tuple(r[0] for r in self.env.cr.fetchall()) or (None,)

    @api.model
    def _get_liquidity_moves(self, options, payment_account_ids, cashflow_tag_ids):
        reconciled_aml_groupby_account = {}

        for col_idx, col in enumerate(options['columns']):
            date_from = fields.Date.to_date(col['date_from'])
            date_to = fields.Date.to_date(col['date_to'])
            move_ids = self._payment_move_ids(options, payment_account_ids, date_from, date_to)
            if move_ids == (None,):
                continue

            self.env.cr.execute(SQL(
                """
                SELECT
                    %(col_idx)s AS column_group_index,
                    account_move_line.account_id,
                    SUM(account_partial_reconcile.amount) AS balance
                FROM account_move_line
                LEFT JOIN account_partial_reconcile
                    ON account_partial_reconcile.credit_move_id = account_move_line.id
                WHERE account_move_line.move_id IN %(move_ids)s
                  AND account_move_line.account_id NOT IN %(payment_account_ids)s
                  AND account_partial_reconcile.max_date BETWEEN %(date_from)s AND %(date_to)s
                  AND %(company)s
                  AND %(state)s
                GROUP BY account_move_line.account_id

                UNION ALL

                SELECT
                    %(col_idx)s AS column_group_index,
                    account_move_line.account_id,
                    -SUM(account_partial_reconcile.amount) AS balance
                FROM account_move_line
                LEFT JOIN account_partial_reconcile
                    ON account_partial_reconcile.debit_move_id = account_move_line.id
                WHERE account_move_line.move_id IN %(move_ids)s
                  AND account_move_line.account_id NOT IN %(payment_account_ids)s
                  AND account_partial_reconcile.max_date BETWEEN %(date_from)s AND %(date_to)s
                  AND %(company)s
                  AND %(state)s
                GROUP BY account_move_line.account_id

                UNION ALL

                SELECT
                    %(col_idx)s AS column_group_index,
                    account_move_line.account_id,
                    SUM(account_move_line.balance) AS balance
                FROM account_move_line
                WHERE account_move_line.move_id IN %(move_ids)s
                  AND account_move_line.account_id NOT IN %(payment_account_ids)s
                  AND %(company)s
                  AND %(state)s
                GROUP BY account_move_line.account_id
                """,
                col_idx=col_idx,
                move_ids=move_ids,
                payment_account_ids=payment_account_ids,
                date_from=date_from,
                date_to=date_to,
                company=self._company_sql(options),
                state=self._state_sql(options),
            ))
            raw = self.env.cr.dictfetchall()
            meta = self._account_meta(
                [r['account_id'] for r in raw], cashflow_tag_ids,
            )
            for aml_data in raw:
                account_id = aml_data['account_id']
                info = meta.get(account_id, {})
                reconciled_aml_groupby_account.setdefault(account_id, {})
                reconciled_aml_groupby_account[account_id].setdefault(col_idx, {
                    'column_group_index': col_idx,
                    'account_id': account_id,
                    'account_code': info.get('account_code'),
                    'account_name': info.get('account_name'),
                    'account_account_type': info.get('account_account_type'),
                    'account_tag_id': info.get('account_tag_id'),
                    'balance': 0.0,
                })
                reconciled_aml_groupby_account[account_id][col_idx]['balance'] -= aml_data['balance']

        return list(reconciled_aml_groupby_account.values())

    # -------------------------------------------------------------------------
    # Reconciled non-liquidity moves (percentage paid)
    # -------------------------------------------------------------------------

    @api.model
    def _get_reconciled_moves(self, options, payment_account_ids, cashflow_tag_ids):
        reconciled_account_ids = {i: set() for i in range(len(options['columns']))}
        reconciled_percentage_per_move = {i: {} for i in range(len(options['columns']))}

        for col_idx, col in enumerate(options['columns']):
            date_from = fields.Date.to_date(col['date_from'])
            date_to = fields.Date.to_date(col['date_to'])
            move_ids = self._payment_move_ids(options, payment_account_ids, date_from, date_to)
            if move_ids == (None,):
                continue

            self.env.cr.execute(SQL(
                """
                SELECT
                    debit_line.move_id,
                    debit_line.account_id,
                    SUM(account_partial_reconcile.amount) AS balance
                FROM account_move_line AS credit_line
                JOIN account_partial_reconcile
                    ON account_partial_reconcile.credit_move_id = credit_line.id
                JOIN account_move_line AS debit_line
                    ON debit_line.id = account_partial_reconcile.debit_move_id
                WHERE credit_line.move_id IN %(move_ids)s
                  AND credit_line.account_id NOT IN %(payment_account_ids)s
                  AND credit_line.credit > 0.0
                  AND debit_line.move_id NOT IN %(move_ids)s
                  AND account_partial_reconcile.max_date BETWEEN %(date_from)s AND %(date_to)s
                GROUP BY debit_line.move_id, debit_line.account_id

                UNION ALL

                SELECT
                    credit_line.move_id,
                    credit_line.account_id,
                    -SUM(account_partial_reconcile.amount) AS balance
                FROM account_move_line AS debit_line
                JOIN account_partial_reconcile
                    ON account_partial_reconcile.debit_move_id = debit_line.id
                JOIN account_move_line AS credit_line
                    ON credit_line.id = account_partial_reconcile.credit_move_id
                WHERE debit_line.move_id IN %(move_ids)s
                  AND debit_line.account_id NOT IN %(payment_account_ids)s
                  AND debit_line.debit > 0.0
                  AND credit_line.move_id NOT IN %(move_ids)s
                  AND account_partial_reconcile.max_date BETWEEN %(date_from)s AND %(date_to)s
                GROUP BY credit_line.move_id, credit_line.account_id
                """,
                move_ids=move_ids,
                payment_account_ids=payment_account_ids,
                date_from=date_from,
                date_to=date_to,
            ))
            for aml_data in self.env.cr.dictfetchall():
                move_id = aml_data['move_id']
                account_id = aml_data['account_id']
                reconciled_percentage_per_move[col_idx].setdefault(move_id, {})
                reconciled_percentage_per_move[col_idx][move_id].setdefault(account_id, [0.0, 0.0])
                reconciled_percentage_per_move[col_idx][move_id][account_id][0] += aml_data['balance']
                reconciled_account_ids[col_idx].add(account_id)

        if not any(reconciled_percentage_per_move.values()):
            return []

        for col_idx in range(len(options['columns'])):
            move_map = reconciled_percentage_per_move[col_idx]
            if not move_map:
                continue
            account_ids = tuple(reconciled_account_ids[col_idx]) or (None,)
            self.env.cr.execute(SQL(
                """
                SELECT
                    account_move_line.move_id,
                    account_move_line.account_id,
                    SUM(account_move_line.balance) AS balance
                FROM account_move_line
                WHERE account_move_line.move_id IN %(move_ids)s
                  AND account_move_line.account_id IN %(account_ids)s
                GROUP BY account_move_line.move_id, account_move_line.account_id
                """,
                move_ids=tuple(move_map.keys()),
                account_ids=account_ids,
            ))
            for aml_data in self.env.cr.dictfetchall():
                if aml_data['account_id'] in move_map.get(aml_data['move_id'], {}):
                    move_map[aml_data['move_id']][aml_data['account_id']][1] += aml_data['balance']

        reconciled_aml_per_account = {}
        for col_idx in range(len(options['columns'])):
            move_map = reconciled_percentage_per_move[col_idx]
            if not move_map:
                continue
            self.env.cr.execute(SQL(
                """
                SELECT
                    account_move_line.move_id,
                    account_move_line.account_id,
                    SUM(account_move_line.balance) AS balance
                FROM account_move_line
                WHERE account_move_line.move_id IN %(move_ids)s
                GROUP BY account_move_line.move_id, account_move_line.account_id
                """,
                move_ids=tuple(move_map.keys()),
            ))
            raw = self.env.cr.dictfetchall()
            meta = self._account_meta(
                list({r['account_id'] for r in raw}), cashflow_tag_ids,
            )
            for aml_data in raw:
                move_id = aml_data['move_id']
                account_id = aml_data['account_id']
                aml_balance = aml_data['balance']
                info = meta.get(account_id, {})

                total_reconciled = 0.0
                total_amount = 0.0
                for reconciled_amount, amount in move_map[move_id].values():
                    total_reconciled += reconciled_amount
                    total_amount += amount

                if total_amount and account_id not in move_map[move_id]:
                    aml_balance *= total_reconciled / total_amount
                elif not total_amount and account_id in move_map[move_id]:
                    aml_balance = -move_map[move_id][account_id][0]
                else:
                    continue

                reconciled_aml_per_account.setdefault(account_id, {})
                reconciled_aml_per_account[account_id].setdefault(col_idx, {
                    'column_group_index': col_idx,
                    'account_id': account_id,
                    'account_code': info.get('account_code'),
                    'account_name': info.get('account_name'),
                    'account_account_type': info.get('account_account_type'),
                    'account_tag_id': info.get('account_tag_id'),
                    'balance': 0.0,
                })
                reconciled_aml_per_account[account_id][col_idx]['balance'] -= aml_balance

        return list(reconciled_aml_per_account.values())
