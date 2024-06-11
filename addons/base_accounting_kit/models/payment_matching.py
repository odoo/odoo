# -*- coding: utf-8 -*-

import copy
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.misc import formatLang, format_date, parse_date


class AccountReconciliation(models.AbstractModel):
    _name = 'account.reconciliation.widget'
    _description = 'Account Reconciliation widget'

    ####################################################
    # Public
    ####################################################

    @api.model
    def process_bank_statement_line(self, st_line_ids, data):
        """Handles data sent from the bank statement reconciliation widget
        (and can otherwise serve as an old-API bridge)

        :param st_line_ids
        :param list of dicts data: must contains the keys
            'counterpart_aml_dicts', 'payment_aml_ids' and 'new_aml_dicts',
            whose value is the same as described in process_reconciliation
            except that ids are used instead of recordsets.
        :returns dict: used as a hook to add additional keys.
        """
        st_lines = self.env['account.bank.statement.line'].browse(st_line_ids)
        AccountMoveLine = self.env['account.move.line']
        ctx = dict(self._context, force_price_include=False)

        processed_moves = self.env['account.move']
        for st_line, datum in zip(st_lines, copy.deepcopy(data)):
            payment_aml_rec = AccountMoveLine.browse(datum.get('payment_aml_ids', []))

            for aml_dict in datum.get('counterpart_aml_dicts', []):
                aml_dict['move_line'] = AccountMoveLine.browse(
                    aml_dict['counterpart_aml_id']
                )
                del aml_dict['counterpart_aml_id']

            if datum.get('partner_id') is not None:
                st_line.write({'partner_id': datum['partner_id']})

            ctx['default_to_check'] = datum.get('to_check')
            moves = st_line.with_context(ctx).process_reconciliation(
                datum.get('counterpart_aml_dicts', []),
                payment_aml_rec,
                datum.get('new_aml_dicts', []))
            processed_moves = (processed_moves | moves)
        return {'moves': processed_moves.ids, 'statement_line_ids': processed_moves.mapped('line_ids.statement_line_id').ids}

    @api.model
    def get_move_lines_for_bank_statement_line(self, st_line_id, partner_id=None, excluded_ids=None, search_str=False, offset=0, limit=None, mode=None):
        """ Returns move lines for the bank statement reconciliation widget,
            formatted as a list of dicts

            :param st_line_id: ids of the statement lines
            :param partner_id: optional partner id to select only the moves
                line corresponding to the partner
            :param excluded_ids: optional move lines ids excluded from the
                result
            :param search_str: optional search (can be the amout, display_name,
                partner name, move line name)
            :param offset: useless but kept in stable to preserve api
            :param limit: number of the result to search
            :param mode: 'rp' for receivable/payable or 'other'
        """
        st_line = self.env['account.bank.statement.line'].browse(st_line_id)

        # Blue lines = payment on bank account not assigned to a statement yet
        aml_accounts = [
            st_line.journal_id.default_account_id.id
        ]

        if partner_id is None:
            partner_id = st_line.partner_id.id

        domain = self._domain_move_lines_for_reconciliation(st_line, aml_accounts, partner_id, excluded_ids=excluded_ids, search_str=search_str, mode=mode)
        recs_count = self.env['account.move.line'].search_count(domain)

        from_clause, where_clause, where_clause_params = self.env['account.move.line']._where_calc(domain).get_sql()
        query_str = '''
            SELECT "account_move_line".id FROM {from_clause}
            {where_str}
            ORDER BY ("account_move_line".debit - "account_move_line".credit) = {amount} DESC,
                "account_move_line".date_maturity ASC,
                "account_move_line".id ASC
            {limit_str}
        '''.format(
            from_clause=from_clause,
            where_str=where_clause and (" WHERE %s" % where_clause) or '',
            amount=st_line.amount,
            limit_str=limit and ' LIMIT %s' or '',
        )
        params = where_clause_params + (limit and [limit] or [])
        self.env['account.move'].flush()
        self.env['account.move.line'].flush()
        self.env['account.bank.statement'].flush()
        self._cr.execute(query_str, params)
        res = self._cr.fetchall()

        aml_recs = self.env['account.move.line'].browse([i[0] for i in res])
        target_currency = st_line.currency_id or st_line.journal_id.currency_id or st_line.journal_id.company_id.currency_id
        return self._prepare_move_lines(aml_recs, target_currency=target_currency, target_date=st_line.date, recs_count=recs_count)

    @api.model
    def _get_bank_statement_line_partners(self, st_lines):
        params = []

        # Add the res.partner.ban's IR rules. In case partners are not shared between companies,
        # identical bank accounts may exist in a company we don't have access to.
        ir_rules_query = self.env['res.partner.bank']._where_calc([])
        self.env['res.partner.bank']._apply_ir_rules(ir_rules_query, 'read')
        from_clause, where_clause, where_clause_params = ir_rules_query.get_sql()
        if where_clause:
            where_bank = ('AND %s' % where_clause).replace('res_partner_bank', 'bank')
            params += where_clause_params
        else:
            where_bank = ''

        # Add the res.partner's IR rules. In case partners are not shared between companies,
        # identical partners may exist in a company we don't have access to.
        ir_rules_query = self.env['res.partner']._where_calc([])
        self.env['res.partner']._apply_ir_rules(ir_rules_query, 'read')
        from_clause, where_clause, where_clause_params = ir_rules_query.get_sql()
        if where_clause:
            where_partner = ('AND %s' % where_clause).replace('res_partner', 'p3')
            params += where_clause_params
        else:
            where_partner = ''

        query = '''
            SELECT
                st_line.id                          AS id,
                COALESCE(p1.id,p2.id,p3.id)         AS partner_id
            FROM account_bank_statement_line st_line
            JOIN account_move move ON move.id = st_line.move_id
        '''
        query += "LEFT JOIN res_partner_bank bank ON bank.id = move.partner_bank_id OR bank.sanitized_acc_number ILIKE regexp_replace(st_line.account_number, '\W+', '', 'g') %s\n" % (where_bank)
        query += 'LEFT JOIN res_partner p1 ON st_line.partner_id=p1.id \n'
        query += 'LEFT JOIN res_partner p2 ON bank.partner_id=p2.id \n'
        # By definition the commercial partner_id doesn't have a parent_id set
        query += 'LEFT JOIN res_partner p3 ON p3.name ILIKE st_line.partner_name %s AND p3.parent_id is NULL \n' % (where_partner)
        query += 'WHERE st_line.id IN %s'

        params += [tuple(st_lines.ids)]

        self._cr.execute(query, params)

        result = {}
        for res in self._cr.dictfetchall():
            result[res['id']] = res['partner_id']
        return result

    @api.model
    def get_bank_statement_line_data(self, st_line_ids, excluded_ids=None):
        """ Returns the data required to display a reconciliation widget, for
            each statement line in self

            :param st_line_id: ids of the statement lines
            :param excluded_ids: optional move lines ids excluded from the
                result
        """
        results = {
            'lines': [],
            'value_min': 0,
            'value_max': 0,
            'reconciled_aml_ids': [],
        }

        if not st_line_ids:
            return results

        excluded_ids = excluded_ids or []

        # Make a search to preserve the table's order.
        bank_statement_lines = self.env['account.bank.statement.line'].search([('id', 'in', st_line_ids)])
        results['value_max'] = len(bank_statement_lines)
        reconcile_model = self.env['account.reconcile.model'].search([('rule_type', '!=', 'writeoff_button')])

        # Search for missing partners when opening the reconciliation widget.
        if bank_statement_lines:
            partner_map = self._get_bank_statement_line_partners(bank_statement_lines)
            matching_amls = reconcile_model._apply_rules(bank_statement_lines, excluded_ids=excluded_ids, partner_map=partner_map)

        # Iterate on st_lines to keep the same order in the results list.
        bank_statements_left = self.env['account.bank.statement']
        for line in bank_statement_lines:
            if matching_amls[line.id].get('status') == 'reconciled':
                reconciled_move_lines = matching_amls[line.id].get('reconciled_lines')
                results['value_min'] += 1
                results['reconciled_aml_ids'] += reconciled_move_lines and reconciled_move_lines.ids or []
            else:
                aml_ids = matching_amls[line.id]['aml_ids']
                bank_statements_left += line.statement_id
                target_currency = line.currency_id or line.journal_id.currency_id or line.journal_id.company_id.currency_id

                amls = aml_ids and self.env['account.move.line'].browse(aml_ids)
                line_vals = {
                    'st_line': self._get_statement_line(line),
                    'reconciliation_proposition': aml_ids and self._prepare_move_lines(amls, target_currency=target_currency, target_date=line.date) or [],
                    'model_id': matching_amls[line.id].get('model') and matching_amls[line.id]['model'].id,
                    'write_off': matching_amls[line.id].get('status') == 'write_off',
                }
                if not line.partner_id and partner_map.get(line.id):
                    partner = self.env['res.partner'].browse(partner_map[line.id])
                    line_vals.update({
                        'partner_id': partner.id,
                        'partner_name': partner.name,
                    })
                results['lines'].append(line_vals)

        return results

    @api.model
    def get_bank_statement_data(self, bank_statement_line_ids, srch_domain=[]):
        """ Get statement lines of the specified statements or all unreconciled
            statement lines and try to automatically reconcile them / find them
            a partner.
            Return ids of statement lines left to reconcile and other data for
            the reconciliation widget.

            :param bank_statement_line_ids: ids of the bank statement lines
        """
        if not bank_statement_line_ids:
            return {}
        domain = [['id', 'in', tuple(bank_statement_line_ids)], ('is_reconciled', '=', False)] + srch_domain
        bank_statement_lines = self.env['account.bank.statement.line'].search(domain)
        bank_statements = bank_statement_lines.mapped('statement_id')

        results = self.get_bank_statement_line_data(bank_statement_lines.ids)
        bank_statement_lines_left = self.env['account.bank.statement.line'].browse([line['st_line']['id'] for line in results['lines']])
        bank_statements_left = bank_statement_lines_left.mapped('statement_id')

        results.update({
            'statement_name': len(bank_statements_left) == 1 and bank_statements_left.name or False,
            'journal_id': bank_statements and bank_statements[0].journal_id.id or False,
            'notifications': []
        })

        if len(results['lines']) < len(bank_statement_lines):
            results['notifications'].append({
                'type': 'info',
                'template': 'reconciliation.notification.reconciled',
                'reconciled_aml_ids': results['reconciled_aml_ids'],
                'nb_reconciled_lines': results['value_min'],
                'details': {
                    'name': _('Journal Items'),
                    'model': 'account.move.line',
                    'ids': results['reconciled_aml_ids'],
                }
            })

        return results

    @api.model
    def get_move_lines_for_manual_reconciliation(self, account_id, partner_id=False, excluded_ids=None, search_str=False, offset=0, limit=None, target_currency_id=False):
        """ Returns unreconciled move lines for an account or a partner+account, formatted for the manual reconciliation widget """

        Account_move_line = self.env['account.move.line']
        Account = self.env['account.account']
        Currency = self.env['res.currency']

        domain = self._domain_move_lines_for_manual_reconciliation(account_id, partner_id, excluded_ids, search_str)
        recs_count = Account_move_line.search_count(domain)
        lines = Account_move_line.search(domain, limit=limit, order="date_maturity desc, id desc")
        if target_currency_id:
            target_currency = Currency.browse(target_currency_id)
        else:
            account = Account.browse(account_id)
            target_currency = account.currency_id or account.company_id.currency_id
        return self._prepare_move_lines(lines, target_currency=target_currency,recs_count=recs_count)

    @api.model
    def get_all_data_for_manual_reconciliation(self, partner_ids, account_ids):
        """ Returns the data required for the invoices & payments matching of partners/accounts.
            If an argument is None, fetch all related reconciliations. Use [] to fetch nothing.
        """
        MoveLine = self.env['account.move.line']
        aml_ids = self._context.get('active_ids') and self._context.get('active_model') == 'account.move.line' and tuple(self._context.get('active_ids'))
        if aml_ids:
            aml = MoveLine.browse(aml_ids)
            account = aml[0].account_id
            currency = account.currency_id or account.company_id.currency_id
            return {
                'accounts': [{
                    'reconciliation_proposition': self._prepare_move_lines(aml, target_currency=currency),
                    'company_id': account.company_id.id,
                    'currency_id': currency.id,
                    'mode': 'accounts',
                    'account_id': account.id,
                    'account_name': account.name,
                    'account_code': account.code,
                }],
                'customers': [],
                'suppliers': [],
            }
        # If we have specified partner_ids, don't return the list of reconciliation for specific accounts as it will
        # show entries that are not reconciled with other partner. Asking for a specific partner on a specific account
        # is never done.
        accounts_data = []
        if not partner_ids or not any(partner_ids):
            accounts_data = self.get_data_for_manual_reconciliation('account', account_ids)
        return {
            'customers': self.get_data_for_manual_reconciliation('partner', partner_ids, 'receivable'),
            'suppliers': self.get_data_for_manual_reconciliation('partner', partner_ids, 'payable'),
            'accounts': accounts_data,
        }

    @api.model
    def get_data_for_manual_reconciliation(self, res_type, res_ids=None, account_type=None):
        """ Returns the data required for the invoices & payments matching of partners/accounts (list of dicts).
            If no res_ids is passed, returns data for all partners/accounts that can be reconciled.

            :param res_type: either 'partner' or 'account'
            :param res_ids: ids of the partners/accounts to reconcile, use None to fetch data indiscriminately
                of the id, use [] to prevent from fetching any data at all.
            :param account_type: if a partner is both customer and vendor, you can use 'payable' to reconcile
                the vendor-related journal entries and 'receivable' for the customer-related entries.
        """

        Account = self.env['account.account']
        Partner = self.env['res.partner']

        if res_ids is not None and len(res_ids) == 0:
            # Note : this short-circuiting is better for performances, but also required
            # since postgresql doesn't implement empty list (so 'AND id in ()' is useless)
            return []
        res_ids = res_ids and tuple(res_ids)

        assert res_type in ('partner', 'account')
        assert account_type in ('payable', 'receivable', None)
        is_partner = res_type == 'partner'
        res_alias = is_partner and 'p' or 'a'
        aml_ids = self._context.get('active_ids') and self._context.get('active_model') == 'account.move.line' and tuple(self._context.get('active_ids'))
        all_entries = self._context.get('all_entries', False)
        all_entries_query = """
            AND EXISTS (
                SELECT NULL
                FROM account_move_line l
                JOIN account_move move ON l.move_id = move.id
                JOIN account_journal journal ON l.journal_id = journal.id
                WHERE l.account_id = a.id
                {inner_where}
                AND l.amount_residual != 0
                AND move.state = 'posted'
            )
        """.format(inner_where=is_partner and 'AND l.partner_id = p.id' or ' ')
        only_dual_entries_query = """
            AND EXISTS (
                SELECT NULL
                FROM account_move_line l
                JOIN account_move move ON l.move_id = move.id
                JOIN account_journal journal ON l.journal_id = journal.id
                WHERE l.account_id = a.id
                {inner_where}
                AND l.amount_residual > 0
                AND move.state = 'posted'
            )
            AND EXISTS (
                SELECT NULL
                FROM account_move_line l
                JOIN account_move move ON l.move_id = move.id
                JOIN account_journal journal ON l.journal_id = journal.id
                WHERE l.account_id = a.id
                {inner_where}
                AND l.amount_residual < 0
                AND move.state = 'posted'
            )
        """.format(inner_where=is_partner and 'AND l.partner_id = p.id' or ' ')
        query = ("""
            SELECT {select} account_id, account_name, account_code, max_date
            FROM (
                    SELECT {inner_select}
                        a.id AS account_id,
                        a.name AS account_name,
                        a.code AS account_code,
                        MAX(l.write_date) AS max_date
                    FROM
                        account_move_line l
                        RIGHT JOIN account_account a ON (a.id = l.account_id)
                        RIGHT JOIN account_account_type at ON (at.id = a.user_type_id)
                        {inner_from}
                    WHERE
                        a.reconcile IS TRUE
                        AND l.full_reconcile_id is NULL
                        {where1}
                        {where2}
                        {where3}
                        AND l.company_id = {company_id}
                        {where4}
                        {where5}
                    GROUP BY {group_by1} a.id, a.name, a.code {group_by2}
                    {order_by}
                ) as s
            {outer_where}
        """.format(
                select=is_partner and "partner_id, partner_name, to_char(last_time_entries_checked, 'YYYY-MM-DD') AS last_time_entries_checked," or ' ',
                inner_select=is_partner and 'p.id AS partner_id, p.name AS partner_name, p.last_time_entries_checked AS last_time_entries_checked,' or ' ',
                inner_from=is_partner and 'RIGHT JOIN res_partner p ON (l.partner_id = p.id)' or ' ',
                where1=is_partner and ' ' or "AND ((at.type <> 'payable' AND at.type <> 'receivable') OR l.partner_id IS NULL)",
                where2=account_type and "AND at.type = %(account_type)s" or '',
                where3=res_ids and 'AND ' + res_alias + '.id in %(res_ids)s' or '',
                company_id=self.env.company.id,
                where4=aml_ids and 'AND l.id IN %(aml_ids)s' or ' ',
                where5=all_entries and all_entries_query or only_dual_entries_query,
                group_by1=is_partner and 'l.partner_id, p.id,' or ' ',
                group_by2=is_partner and ', p.last_time_entries_checked' or ' ',
                order_by=is_partner and 'ORDER BY p.last_time_entries_checked' or 'ORDER BY a.code',
                outer_where=is_partner and 'WHERE (last_time_entries_checked IS NULL OR max_date > last_time_entries_checked)' or ' ',
            ))
        self.env['account.move.line'].flush()
        self.env['account.account'].flush()
        self.env.cr.execute(query, locals())

        # Apply ir_rules by filtering out
        rows = self.env.cr.dictfetchall()
        ids = [x['account_id'] for x in rows]
        allowed_ids = set(Account.browse(ids).ids)
        rows = [row for row in rows if row['account_id'] in allowed_ids]
        if is_partner:
            ids = [x['partner_id'] for x in rows]
            allowed_ids = set(Partner.browse(ids).ids)
            rows = [row for row in rows if row['partner_id'] in allowed_ids]

        # Keep mode for future use in JS
        if res_type == 'account':
            mode = 'accounts'
        else:
            mode = 'customers' if account_type == 'receivable' else 'suppliers'

        # Fetch other data
        for row in rows:
            account = Account.browse(row['account_id'])
            currency = account.currency_id or account.company_id.currency_id
            row['currency_id'] = currency.id
            partner_id = is_partner and row['partner_id'] or None
            rec_prop = aml_ids and self.env['account.move.line'].browse(aml_ids) or self._get_move_line_reconciliation_proposition(account.id, partner_id)
            row['reconciliation_proposition'] = self._prepare_move_lines(rec_prop, target_currency=currency)
            row['mode'] = mode
            row['company_id'] = account.company_id.id

        # Return the partners with a reconciliation proposition first, since they are most likely to
        # be reconciled.
        return [r for r in rows if r['reconciliation_proposition']] + [r for r in rows if not r['reconciliation_proposition']]

    @api.model
    def process_move_lines(self, data):
        """ Used to validate a batch of reconciliations in a single call
            :param data: list of dicts containing:
                - 'type': either 'partner' or 'account'
                - 'id': id of the affected res.partner or account.account
                - 'mv_line_ids': ids of existing account.move.line to reconcile
                - 'new_mv_line_dicts': list of dicts containing values suitable for account_move_line.create()
        """

        Partner = self.env['res.partner']
        Account = self.env['account.account']

        for datum in data:
            if len(datum['mv_line_ids']) >= 1 or len(datum['mv_line_ids']) + len(datum['new_mv_line_dicts']) >= 2:
                self._process_move_lines(datum['mv_line_ids'], datum['new_mv_line_dicts'])

            if datum['type'] == 'partner':
                partners = Partner.browse(datum['id'])
                partners.mark_as_reconciled()

    ####################################################
    # Private
    ####################################################

    def _str_domain_for_mv_line(self, search_str):
        return [
            '|', ('account_id.code', 'ilike', search_str),
            '|', ('move_id.name', 'ilike', search_str),
            '|', ('move_id.ref', 'ilike', search_str),
            '|', ('date_maturity', 'like', parse_date(self.env, search_str)),
            '&', ('name', '!=', '/'), ('name', 'ilike', search_str)
        ]

    @api.model
    def _domain_move_lines(self, search_str):
        """ Returns the domain from the search_str search
            :param search_str: search string
        """
        if not search_str:
            return []
        str_domain = self._str_domain_for_mv_line(search_str)
        if search_str[0] in ['-', '+']:
            try:
                amounts_str = search_str.split('|')
                for amount_str in amounts_str:
                    amount = amount_str[0] == '-' and float(amount_str) or float(amount_str[1:])
                    amount_domain = [
                        '|', ('amount_residual', '=', amount),
                        '|', ('amount_residual_currency', '=', amount),
                        '|', (amount_str[0] == '-' and 'credit' or 'debit', '=', float(amount_str[1:])),
                        ('amount_currency', '=', amount),
                    ]
                    str_domain = expression.OR([str_domain, amount_domain])
            except:
                pass
        else:
            try:
                amount = float(search_str)
                amount_domain = [
                    '|', ('amount_residual', '=', amount),
                    '|', ('amount_residual_currency', '=', amount),
                    '|', ('amount_residual', '=', -amount),
                    '|', ('amount_residual_currency', '=', -amount),
                    '&', ('account_id.internal_type', '=', 'liquidity'),
                    '|', '|', '|', ('debit', '=', amount), ('credit', '=', amount), ('amount_currency', '=', amount), ('amount_currency', '=', -amount),
                ]
                str_domain = expression.OR([str_domain, amount_domain])
            except:
                pass
        return str_domain

    @api.model
    def _domain_move_lines_for_reconciliation(self, st_line, aml_accounts, partner_id, excluded_ids=[], search_str=False, mode='rp'):
        """ Return the domain for account.move.line records which can be used for bank statement reconciliation.

            :param aml_accounts:
            :param partner_id:
            :param excluded_ids:
            :param search_str:
            :param mode: 'rp' for receivable/payable or 'other'
        """
        AccountMoveLine = self.env['account.move.line']

        #Always exclude the journal items that have been marked as 'to be checked' in a former bank statement reconciliation
        to_check_excluded = AccountMoveLine.search(AccountMoveLine._get_suspense_moves_domain()).ids
        excluded_ids.extend(to_check_excluded)

        domain_reconciliation = [
            '&', '&', '&',
            ('statement_line_id', '=', False),
            ('account_id', 'in', aml_accounts),
            ('payment_id', '<>', False),
            ('balance', '!=', 0.0),
        ]

        # default domain matching
        domain_matching = [
            '&', '&',
            ('reconciled', '=', False),
            ('account_id.reconcile', '=', True),
            ('balance', '!=', 0.0),
        ]

        domain = expression.OR([domain_reconciliation, domain_matching])
        if partner_id:
            domain = expression.AND([domain, [('partner_id', '=', partner_id)]])
        if mode == 'rp':
            domain = expression.AND([domain,
            [('account_id.internal_type', 'in', ['receivable', 'payable', 'liquidity'])]
            ])
        else:
            domain = expression.AND([domain,
            [('account_id.internal_type', 'not in', ['receivable', 'payable', 'liquidity'])]
            ])

        # Domain factorized for all reconciliation use cases
        if search_str:
            str_domain = self._domain_move_lines(search_str=search_str)
            str_domain = expression.OR([
                str_domain,
                [('partner_id.name', 'ilike', search_str)]
            ])
            domain = expression.AND([
                domain,
                str_domain
            ])

        if excluded_ids:
            domain = expression.AND([
                [('id', 'not in', excluded_ids)],
                domain
            ])
        # filter on account.move.line having the same company as the statement line
        domain = expression.AND([domain, [('company_id', '=', st_line.company_id.id)]])

        # take only moves in valid state. Draft is accepted only when "Post At" is set
        # to "Bank Reconciliation" in the associated journal
        domain_post_at = [

            ('move_id.state', 'not in', ['draft', 'cancel']),
        ]
        domain = expression.AND([domain, domain_post_at])

        if st_line.company_id.account_bank_reconciliation_start:
            domain = expression.AND([domain, [('date', '>=', st_line.company_id.account_bank_reconciliation_start)]])
        return domain

    @api.model
    def _domain_move_lines_for_manual_reconciliation(self, account_id, partner_id=False, excluded_ids=None, search_str=False):
        """ Create domain criteria that are relevant to manual reconciliation. """
        domain = [
                    ('reconciled', '=', False),
                    ('account_id', '=', account_id),
                    ('move_id.state', '=', 'posted')
            ]
        domain = expression.AND([domain, [('balance', '!=', 0.0)]])
        if partner_id:
            domain = expression.AND([domain, [('partner_id', '=', partner_id)]])
        if excluded_ids:
            domain = expression.AND([[('id', 'not in', excluded_ids)], domain])
        if search_str:
            str_domain = self._domain_move_lines(search_str=search_str)
            domain = expression.AND([domain, str_domain])
        # filter on account.move.line having the same company as the given account
        account = self.env['account.account'].browse(account_id)
        domain = expression.AND([domain, [('company_id', '=', account.company_id.id)]])
        return domain

    @api.model
    def _prepare_move_lines(self, move_lines, target_currency=False, target_date=False, recs_count=0):
        """ Returns move lines formatted for the manual/bank reconciliation widget

            :param move_line_ids:
            :param target_currency: currency (browse) you want the move line debit/credit converted into
            :param target_date: date to use for the monetary conversion
        """
        context = dict(self._context or {})
        ret = []

        for line in move_lines:
            company_currency = line.company_id.currency_id
            line_currency = (line.currency_id and line.amount_currency) and line.currency_id or company_currency
            ret_line = {
                'id': line.id,
                'name': line.name and line.name != '/' and line.move_id.name != line.name and line.move_id.name + ': ' + line.name or line.move_id.name,
                'ref': line.move_id.ref or '',
                # For reconciliation between statement transactions and already registered payments (eg. checks)
                # NB : we don't use the 'reconciled' field because the line we're selecting is not the one that gets reconciled
                'account_id': [line.account_id.id, line.account_id.display_name],
                'already_paid': line.account_id.internal_type == 'liquidity',
                'account_code': line.account_id.code,
                'account_name': line.account_id.name,
                'account_type': line.account_id.internal_type,
                'date_maturity': format_date(self.env, line.date_maturity),
                'date': format_date(self.env, line.date),
                'journal_id': [line.journal_id.id, line.journal_id.display_name],
                'partner_id': line.partner_id.id,
                'partner_name': line.partner_id.name,
                'currency_id': line_currency.id,
            }

            debit = line.debit
            credit = line.credit
            amount = line.amount_residual
            amount_currency = line.amount_residual_currency

            # For already reconciled lines, don't use amount_residual(_currency)
            if line.account_id.internal_type == 'liquidity':
                amount = debit - credit
                amount_currency = line.amount_currency

            target_currency = target_currency or company_currency

            # Use case:
            # Let's assume that company currency is in USD and that we have the 3 following move lines
            #      Debit  Credit  Amount currency  Currency
            # 1)    25      0            0            NULL
            # 2)    17      0           25             EUR
            # 3)    33      0           25             YEN
            #
            # If we ask to see the information in the reconciliation widget in company currency, we want to see
            # The following information
            # 1) 25 USD (no currency information)
            # 2) 17 USD [25 EUR] (show 25 euro in currency information, in the little bill)
            # 3) 33 USD [25 YEN] (show 25 yen in currency information)
            #
            # If we ask to see the information in another currency than the company let's say EUR
            # 1) 35 EUR [25 USD]
            # 2) 25 EUR (no currency information)
            # 3) 50 EUR [25 YEN]
            # In that case, we have to convert the debit-credit to the currency we want and we show next to it
            # the value of the amount_currency or the debit-credit if no amount currency
            if target_currency == company_currency:
                if line_currency == target_currency:
                    amount = amount
                    amount_currency = ""
                    total_amount = debit - credit
                    total_amount_currency = ""
                else:
                    amount = amount
                    amount_currency = amount_currency
                    total_amount = debit - credit
                    total_amount_currency = line.amount_currency

            if target_currency != company_currency:
                if line_currency == target_currency:
                    amount = amount_currency
                    amount_currency = ""
                    total_amount = line.amount_currency
                    total_amount_currency = ""
                else:
                    amount_currency = line.currency_id and amount_currency or amount
                    company = line.account_id.company_id
                    date = target_date or line.date
                    amount = company_currency._convert(amount, target_currency, company, date)
                    total_amount = company_currency._convert((line.debit - line.credit), target_currency, company, date)
                    total_amount_currency = line.currency_id and line.amount_currency or (line.debit - line.credit)

            ret_line['recs_count'] = recs_count
            ret_line['debit'] = amount > 0 and amount or 0
            ret_line['credit'] = amount < 0 and -amount or 0
            ret_line['amount_currency'] = amount_currency
            ret_line['amount_str'] = formatLang(self.env, abs(amount), currency_obj=target_currency)
            ret_line['total_amount_str'] = formatLang(self.env, abs(total_amount), currency_obj=target_currency)
            ret_line['amount_currency_str'] = amount_currency and formatLang(self.env, abs(amount_currency), currency_obj=line_currency) or ""
            ret_line['total_amount_currency_str'] = total_amount_currency and formatLang(self.env, abs(total_amount_currency), currency_obj=line_currency) or ""
            ret.append(ret_line)
        return ret

    @api.model
    def _get_statement_line(self, st_line):
        """ Returns the data required by the bank statement reconciliation widget to display a statement line """

        statement_currency = st_line.journal_id.currency_id or st_line.journal_id.company_id.currency_id
        if st_line.amount_currency and st_line.currency_id:
            amount = st_line.amount_currency
            amount_currency = st_line.amount
            amount_currency_str = formatLang(self.env, abs(amount_currency), currency_obj=statement_currency)
        else:
            amount = st_line.amount
            amount_currency = amount
            amount_currency_str = ""
        amount_str = formatLang(self.env, abs(amount), currency_obj=st_line.currency_id or statement_currency)

        data = {
            'id': st_line.id,
            'ref': st_line.ref,
            'note': st_line.narration or "",
            'name': st_line.name,
            'date': format_date(self.env, st_line.date),
            'amount': amount,
            'amount_str': amount_str,  # Amount in the statement line currency
            'currency_id': st_line.currency_id.id or statement_currency.id,
            'partner_id': st_line.partner_id.id,
            'journal_id': st_line.journal_id.id,
            'statement_id': st_line.statement_id.id,
            'account_id': [st_line.journal_id.default_account_id.id, st_line.journal_id.default_account_id.display_name],
            'account_code': st_line.journal_id.default_account_id.code,
            'account_name': st_line.journal_id.default_account_id.name,
            'partner_name': st_line.partner_id.name,
            'communication_partner_name': st_line.partner_name,
            'amount_currency_str': amount_currency_str,  # Amount in the statement currency
            'amount_currency': amount_currency,  # Amount in the statement currency
            'has_no_partner': not st_line.partner_id.id,
            'company_id': st_line.company_id.id,
        }
        if st_line.partner_id:
            data['open_balance_account_id'] = amount > 0 and st_line.partner_id.property_account_receivable_id.id or st_line.partner_id.property_account_payable_id.id

        return data

    @api.model
    def _get_move_line_reconciliation_proposition(self, account_id, partner_id=None):
        """ Returns two lines whose amount are opposite """

        Account_move_line = self.env['account.move.line']

        ir_rules_query = Account_move_line._where_calc([])
        Account_move_line._apply_ir_rules(ir_rules_query, 'read')
        from_clause, where_clause, where_clause_params = ir_rules_query.get_sql()
        where_str = where_clause and (" WHERE %s" % where_clause) or ''

        # Get pairs
        query = """
            SELECT a.id, b.id
            FROM account_move_line a, account_move_line b,
                 account_move move_a, account_move move_b,
                 account_journal journal_a, account_journal journal_b
            WHERE a.id != b.id
            AND move_a.id = a.move_id
            AND move_a.state = 'posted'
            AND move_a.journal_id = journal_a.id
            AND move_b.id = b.move_id
            AND move_b.journal_id = journal_b.id
            AND move_b.state = 'posted'
            AND a.amount_residual = -b.amount_residual
            AND a.balance != 0.0
            AND b.balance != 0.0
            AND NOT a.reconciled
            AND a.account_id = %s
            AND (%s IS NULL AND b.account_id = %s)
            AND (%s IS NULL AND NOT b.reconciled OR b.id = %s)
            AND (%s is NULL OR (a.partner_id = %s AND b.partner_id = %s))
            AND a.id IN (SELECT "account_move_line".id FROM {0})
            AND b.id IN (SELECT "account_move_line".id FROM {0})
            ORDER BY a.date desc
            LIMIT 1
            """.format(from_clause + where_str)
        move_line_id = self.env.context.get('move_line_id') or None
        params = [
            account_id,
            move_line_id, account_id,
            move_line_id, move_line_id,
            partner_id, partner_id, partner_id,
        ] + where_clause_params + where_clause_params
        self.env.cr.execute(query, params)

        pairs = self.env.cr.fetchall()

        if pairs:
            return Account_move_line.browse(pairs[0])
        return Account_move_line

    @api.model
    def _process_move_lines(self, move_line_ids, new_mv_line_dicts):
        """ Create new move lines from new_mv_line_dicts (if not empty) then call reconcile_partial on self and new move lines

            :param new_mv_line_dicts: list of dicts containing values suitable for account_move_line.create()
        """
        if len(move_line_ids) < 1 or len(move_line_ids) + len(new_mv_line_dicts) < 2:
            raise UserError(_('A reconciliation must involve at least 2 move lines.'))

        account_move_line = self.env['account.move.line'].browse(move_line_ids)
        writeoff_lines = self.env['account.move.line']

        # Create writeoff move lines
        if len(new_mv_line_dicts) > 0:
            company_currency = account_move_line[0].account_id.company_id.currency_id
            same_currency = False
            currencies = list(set([aml.currency_id or company_currency for aml in account_move_line]))
            if len(currencies) == 1 and currencies[0] != company_currency:
                same_currency = True
            # We don't have to convert debit/credit to currency as all values in the reconciliation widget are displayed in company currency
            # If all the lines are in the same currency, create writeoff entry with same currency also
            for mv_line_dict in new_mv_line_dicts:
                if not same_currency:
                    mv_line_dict['amount_currency'] = False
                writeoff_lines += account_move_line._create_writeoff([mv_line_dict])

            (account_move_line + writeoff_lines).reconcile()
        else:
            account_move_line.reconcile()


class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'

    def _create_writeoff(self, writeoff_vals):
        """ Create a writeoff move per journal for the account.move.lines in self. If debit/credit is not specified in vals,
            the writeoff amount will be computed as the sum of amount_residual of the given recordset.
            :param writeoff_vals: list of dicts containing values suitable for account_move_line.create(). The data in vals will
                be processed to create bot writeoff account.move.line and their enclosing account.move.
        """
        def compute_writeoff_counterpart_vals(values):
            line_values = values.copy()
            line_values['debit'], line_values['credit'] = line_values['credit'], line_values['debit']
            if 'amount_currency' in values:
                line_values['amount_currency'] = -line_values['amount_currency']
            return line_values
        # Group writeoff_vals by journals
        writeoff_dict = {}
        for val in writeoff_vals:
            journal_id = val.get('journal_id', False)
            if not writeoff_dict.get(journal_id, False):
                writeoff_dict[journal_id] = [val]
            else:
                writeoff_dict[journal_id].append(val)

        partner_id = self.env['res.partner']._find_accounting_partner(self[0].partner_id).id
        company_currency = self[0].account_id.company_id.currency_id
        writeoff_currency = self[0].account_id.currency_id or company_currency
        line_to_reconcile = self.env['account.move.line']
        # Iterate and create one writeoff by journal
        writeoff_moves = self.env['account.move']
        for journal_id, lines in writeoff_dict.items():
            total = 0
            total_currency = 0
            writeoff_lines = []
            date = fields.Date.today()
            for vals in lines:
                # Check and complete vals
                if 'account_id' not in vals or 'journal_id' not in vals:
                    raise UserError(_("It is mandatory to specify an account and a journal to create a write-off."))
                if ('debit' in vals) ^ ('credit' in vals):
                    raise UserError(_("Either pass both debit and credit or none."))
                if 'date' not in vals:
                    vals['date'] = self._context.get('date_p') or fields.Date.today()
                vals['date'] = fields.Date.to_date(vals['date'])
                if vals['date'] and vals['date'] < date:
                    date = vals['date']
                if 'name' not in vals:
                    vals['name'] = self._context.get('comment') or _('Write-Off')
                if 'analytic_account_id' not in vals:
                    vals['analytic_account_id'] = self.env.context.get('analytic_id', False)
                #compute the writeoff amount if not given
                if 'credit' not in vals and 'debit' not in vals:
                    amount = sum([r.amount_residual for r in self])
                    vals['credit'] = amount > 0 and amount or 0.0
                    vals['debit'] = amount < 0 and abs(amount) or 0.0
                vals['partner_id'] = partner_id
                total += vals['debit']-vals['credit']
                if 'amount_currency' not in vals and writeoff_currency != company_currency:
                    vals['currency_id'] = writeoff_currency.id
                    sign = 1 if vals['debit'] > 0 else -1
                    vals['amount_currency'] = sign * abs(sum([r.amount_residual_currency for r in self]))
                    total_currency += vals['amount_currency']

                writeoff_lines.append(compute_writeoff_counterpart_vals(vals))

            # Create balance line
            writeoff_lines.append({
                'name': _('Write-Off'),
                'debit': total > 0 and total or 0.0,
                'credit': total < 0 and -total or 0.0,
                'amount_currency': total_currency,
                'currency_id': total_currency and writeoff_currency.id or False,
                'journal_id': journal_id,
                'account_id': self[0].account_id.id,
                'partner_id': partner_id
                })

            # Create the move
            writeoff_move = self.env['account.move'].create({
                'journal_id': journal_id,
                'date': date,
                'state': 'draft',
                'line_ids': [(0, 0, line) for line in writeoff_lines],
            })
            writeoff_moves += writeoff_move
            line_to_reconcile += writeoff_move.line_ids.filtered(lambda r: r.account_id == self[0].account_id).sorted(key='id')[-1:]

        #post all the writeoff moves at once
        if writeoff_moves:
            writeoff_moves.action_post()

        # Return the writeoff move.line which is to be reconciled
        return line_to_reconcile


class AccountBankStatement(models.Model):

    _inherit = "account.bank.statement"

    accounting_date = fields.Date(string="Accounting Date",
                                  help="If set, the accounting entries created during the bank statement reconciliation process will be created at this date.\n"
                                       "This is useful if the accounting period in which the entries should normally be booked is already closed.",
                                  states={'open': [('readonly', False)]}, readonly=True)

    def action_bank_reconcile_bank_statements(self):
        self.ensure_one()
        bank_stmt_lines = self.mapped('line_ids')
        return {
            'type': 'ir.actions.client',
            'tag': 'bank_statement_reconciliation_view',
            'context': {'statement_line_ids': bank_stmt_lines.ids, 'company_ids': self.mapped('company_id').ids},
        }


class AccountBankStatementLine(models.Model):

    _inherit = "account.bank.statement.line"

    move_name = fields.Char(string='Journal Entry Name', readonly=True,
                            default=False, copy=False,
                            help="Technical field holding the number given to the journal entry, automatically set when the statement line is reconciled then stored to set the same number again if the line is cancelled, set to draft and re-processed again.")

    def process_reconciliation(self, counterpart_aml_dicts=None, payment_aml_rec=None, new_aml_dicts=None):
        """Match statement lines with existing payments (eg. checks) and/or
        payables/receivables (eg. invoices and credit notes) and/or new move
        lines (eg. write-offs).
        If any new journal item needs to be created (via new_aml_dicts or
        counterpart_aml_dicts), a new journal entry will be created and will
        contain those items, as well as a journal item for the bank statement
        line.
        Finally, mark the statement line as reconciled by putting the matched
        moves ids in the column journal_entry_ids.

        :param self: browse collection of records that are supposed to have no
            accounting entries already linked.
        :param (list of dicts) counterpart_aml_dicts: move lines to create to
            reconcile with existing payables/receivables.
            The expected keys are :
            - 'name'
            - 'debit'
            - 'credit'
            - 'move_line'
                # The move line to reconcile (partially if specified
                # debit/credit is lower than move line's credit/debit)

        :param (list of recordsets) payment_aml_rec: recordset move lines
            representing existing payments (which are already fully reconciled)

        :param (list of dicts) new_aml_dicts: move lines to create. The expected
            keys are :
            - 'name'
            - 'debit'
            - 'credit'
            - 'account_id'
            - (optional) 'tax_ids'
            - (optional) Other account.move.line fields like analytic_account_id
                or analytics_id
            - (optional) 'reconcile_model_id'

        :returns: The journal entries with which the transaction was matched.
            If there was at least an entry in counterpart_aml_dicts or
            new_aml_dicts, this list contains the move created by the
            reconciliation, containing entries for the statement.line (1), the
            counterpart move lines (0..*) and the new move lines (0..*).
        """
        payable_account_type = self.env.ref("account.data_account_type_payable")
        receivable_account_type = self.env.ref("account.data_account_type_receivable")
        suspense_moves_mode = self._context.get("suspense_moves_mode")
        counterpart_aml_dicts = counterpart_aml_dicts or []
        payment_aml_rec = payment_aml_rec or self.env["account.move.line"]
        new_aml_dicts = new_aml_dicts or []

        aml_obj = self.env["account.move.line"]

        company_currency = self.journal_id.company_id.currency_id
        statement_currency = self.journal_id.currency_id or company_currency

        counterpart_moves = self.env["account.move"]

        # Check and prepare received data
        if any(rec.statement_id for rec in payment_aml_rec):
            raise UserError(_("A selected move line was already reconciled."))
        for aml_dict in counterpart_aml_dicts:
            if aml_dict["move_line"].reconciled and not suspense_moves_mode:
                raise UserError(_("A selected move line was already reconciled."))
            if isinstance(aml_dict["move_line"], int):
                aml_dict["move_line"] = aml_obj.browse(aml_dict["move_line"])

        account_types = self.env["account.account.type"]
        for aml_dict in counterpart_aml_dicts + new_aml_dicts:
            if aml_dict.get("tax_ids") and isinstance(aml_dict["tax_ids"][0], int):
                # Transform the value in the format required for One2many and
                # Many2many fields
                aml_dict["tax_ids"] = [(4, id, None) for id in aml_dict["tax_ids"]]

            user_type_id = (
                self.env["account.account"]
                .browse(aml_dict.get("account_id"))
                .user_type_id
            )
            if (
                user_type_id in [payable_account_type, receivable_account_type]
                and user_type_id not in account_types
            ):
                account_types |= user_type_id
        # Fully reconciled moves are just linked to the bank statement
        total = self.amount
        currency = self.currency_id or statement_currency
        for aml_rec in payment_aml_rec:
            balance = (
                aml_rec.amount_currency if aml_rec.currency_id else aml_rec.balance
            )
            aml_currency = aml_rec.currency_id or aml_rec.company_currency_id
            total -= aml_currency._convert(
                balance, currency, aml_rec.company_id, aml_rec.date
            )
            aml_rec.with_context(check_move_validity=False).write({"statement_line_id": self.id})
            counterpart_moves = counterpart_moves | aml_rec.move_id
            # Update
            if aml_rec.payment_id and aml_rec.move_id.state == "draft":
                # In case the journal is set to only post payments when performing bank
                #reconciliation, we modify its date and post it.
                aml_rec.move_id.date = self.date
                aml_rec.payment_id.payment_date = self.date
                aml_rec.move_id.action_post()
                # We check the paid status of the invoices reconciled with this payment
                for invoice in aml_rec.payment_id.reconciled_invoice_ids:
                    self._check_invoice_state(invoice)

        # Create move line(s). Either matching an existing journal entry  (eg. invoice), in which
        # case we reconcile the existing and the new move lines together, or being a write-off.
        if counterpart_aml_dicts or new_aml_dicts:
            aml_obj = self.env["account.move.line"]
            self.move_id.line_ids.with_context(force_delete=True).unlink()
            liquidity_aml_dict = self._prepare_liquidity_move_line_vals()
            aml_obj.with_context(check_move_validity=False).create(liquidity_aml_dict)

            self.sequence = self.statement_id.line_ids.ids.index(self.id) + 1
            counterpart_moves = counterpart_moves | self.move_id

            # Complete dicts to create both counterpart move lines and write-offs
            to_create = counterpart_aml_dicts + new_aml_dicts
            date = self.date or fields.Date.today()
            for aml_dict in to_create:
                aml_dict["move_id"] = self.move_id.id
                aml_dict["partner_id"] = self.partner_id.id
                aml_dict["statement_line_id"] = self.id
                self._prepare_move_line_for_currency(aml_dict, date)

            # Create write-offs
            for aml_dict in new_aml_dicts:
                aml_obj.with_context(check_move_validity=False).create(aml_dict)

            # Create counterpart move lines and reconcile them
            aml_to_reconcile = []
            for aml_dict in counterpart_aml_dicts:
                if not aml_dict["move_line"].statement_line_id:
                    aml_dict["move_line"].write({"statement_line_id": self.id})
                if aml_dict["move_line"].partner_id.id:
                    aml_dict["partner_id"] = aml_dict["move_line"].partner_id.id
                aml_dict["account_id"] = aml_dict["move_line"].account_id.id

                counterpart_move_line = aml_dict.pop("move_line")
                new_aml = aml_obj.with_context(check_move_validity=False).create(aml_dict)

                aml_to_reconcile.append((new_aml, counterpart_move_line))

            # Post to allow reconcile
            if self.move_id.state == 'draft':
                self.move_id.with_context(skip_account_move_synchronization=True).action_post()

            # Reconcile new lines with counterpart
            for new_aml, counterpart_move_line in aml_to_reconcile:
                (new_aml | counterpart_move_line).reconcile()

                self._check_invoice_state(counterpart_move_line.move_id)

            # Needs to be called manually as lines were created 1 by 1
            if self.move_id.state == 'draft':
                self.move_id.with_context(skip_account_move_synchronization=True).action_post()
            # record the move name on the statement line to be able to retrieve
            # it in case of unreconciliation
            self.write({"move_name": self.move_id.name})

        elif self.move_name:
            raise UserError(_('Operation not allowed. Since your statement line already received a number (%s), you cannot reconcile it entirely with existing journal entries otherwise it would make a gap in the numbering. You should book an entry and make a regular revert of it in case you want to cancel it.')% (self.move_name))

        # create the res.partner.bank if needed
        if self.account_number and self.partner_id and not self.bank_account_id:
            # Search bank account without partner to handle the case the res.partner.bank already exists but is set
            # on a different partner.
            self.partner_bank_id = self._find_or_create_bank_account()

        counterpart_moves._check_balanced()
        return counterpart_moves

    def _prepare_move_line_for_currency(self, aml_dict, date):
        self.ensure_one()
        company_currency = self.journal_id.company_id.currency_id
        statement_currency = self.journal_id.currency_id or company_currency
        st_line_currency = self.currency_id or statement_currency
        st_line_currency_rate = self.currency_id and (self.amount_currency / self.amount) or False
        company = self.company_id

        if st_line_currency.id != company_currency.id:
            aml_dict['amount_currency'] = aml_dict['debit'] - aml_dict['credit']
            aml_dict['currency_id'] = st_line_currency.id
            if self.currency_id and statement_currency.id == company_currency.id and st_line_currency_rate:
                # Statement is in company currency but the transaction is in foreign currency
                aml_dict['debit'] = company_currency.round(aml_dict['debit'] / st_line_currency_rate)
                aml_dict['credit'] = company_currency.round(aml_dict['credit'] / st_line_currency_rate)
            elif self.currency_id and st_line_currency_rate:
                # Statement is in foreign currency and the transaction is in another one
                aml_dict['debit'] = statement_currency._convert(aml_dict['debit'] / st_line_currency_rate, company_currency, company, date)
                aml_dict['credit'] = statement_currency._convert(aml_dict['credit'] / st_line_currency_rate, company_currency, company, date)
            else:
                # Statement is in foreign currency and no extra currency is given for the transaction
                aml_dict['debit'] = st_line_currency._convert(aml_dict['debit'], company_currency, company, date)
                aml_dict['credit'] = st_line_currency._convert(aml_dict['credit'], company_currency, company, date)
        elif statement_currency.id != company_currency.id:
            # Statement is in foreign currency but the transaction is in company currency
            prorata_factor = (aml_dict['debit'] - aml_dict['credit']) / self.amount_currency
            aml_dict['amount_currency'] = prorata_factor * self.amount
            aml_dict['currency_id'] = statement_currency.id

    def _check_invoice_state(self, invoice):
        if invoice.is_invoice(include_receipts=True):
            invoice._compute_amount()


class ResCompany(models.Model):
    _inherit = "res.company"

    account_bank_reconciliation_start = fields.Date(string="Bank Reconciliation Threshold", help="""The bank reconciliation widget won't ask to reconcile payments older than this date.
                                                                                                           This is useful if you install accounting after having used invoicing for some time and
                                                                                                           don't want to reconcile all the past payments with bank statements.""")
