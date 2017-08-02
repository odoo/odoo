# -*- coding: utf-8 -*-

import time
from odoo import api, models
from odoo.tools import float_round
from odoo.tools.misc import formatLang
from odoo.osv import expression
from odoo.tools import pycompat


class Reconciliation(models.AbstractModel):
    _name = 'account.reconciliation'

    ####################################################
    # account.bank.statement
    ####################################################

    @api.model
    def reconciliation_widget_preprocess(self, statement_ids):
        """ Get statement lines of the specified statements or all unreconciled statement lines and try to automatically reconcile them / find them a partner.
            Return ids of statement lines left to reconcile and other data for the reconciliation widget.
        """
        user = self.env.user
        cr = self.env.cr
        Statement = self.env['account.bank.statement']
        Statement_line = self.env['account.bank.statement.line']
        statements = Statement.browse(statement_ids)

        # NB : The field account_id can be used at the statement line creation/import to avoid the reconciliation process on it later on,
        # this is why we filter out statements lines where account_id is set

        sql_query = """SELECT stl.id
                        FROM account_bank_statement_line stl
                        WHERE account_id IS NULL AND not exists (select 1 from account_move_line aml where aml.statement_line_id = stl.id)
                            AND company_id = %s
                """
        params = (self.env.user.company_id.id,)
        if statement_ids:
            sql_query += ' AND stl.statement_id IN %s'
            params += (tuple(statement_ids),)
        sql_query += ' ORDER BY stl.id'
        self.env.cr.execute(sql_query, params)
        st_lines_left = self.env['account.bank.statement.line'].browse([line.get('id') for line in self.env.cr.dictfetchall()])

        #try to assign partner to bank_statement_line
        stl_to_assign_partner = [stl.id for stl in st_lines_left if not stl.partner_id]
        refs = list(set([st.name for st in st_lines_left if not stl.partner_id]))
        if st_lines_left and stl_to_assign_partner and refs:
            sql_query = """SELECT aml.partner_id, aml.ref, stl.id
                            FROM account_move_line aml
                                JOIN account_account acc ON acc.id = aml.account_id
                                JOIN account_bank_statement_line stl ON aml.ref = stl.name
                            WHERE (aml.company_id = %s 
                                AND aml.partner_id IS NOT NULL) 
                                AND (
                                    (aml.statement_id IS NULL AND aml.account_id IN %s) 
                                    OR 
                                    (acc.internal_type IN ('payable', 'receivable') AND aml.reconciled = false)
                                    )
                                AND aml.ref IN %s
                                """
            params = (self.env.user.company_id.id, (st_lines_left[0].journal_id.default_credit_account_id.id, st_lines_left[0].journal_id.default_debit_account_id.id), tuple(refs))
            if statement_ids:
                sql_query += 'AND stl.id IN %s'
                params += (tuple(stl_to_assign_partner),)
            self.env.cr.execute(sql_query, params)
            results = self.env.cr.dictfetchall()
            st_line = self.env['account.bank.statement.line']
            for line in results:
                st_line.browse(line.get('id')).write({'partner_id': line.get('partner_id')})

        return {
            'st_lines_ids': st_lines_left.ids,
            'notifications': [],
            'statement_name': len(statement_ids) == 1 and statements[0].name or False,
            'journal_id': statement_ids and statements[0].journal_id.id or False,
            'num_already_reconciled_lines': 0,
        }

    ####################################################
    # account.bank.statement.line
    ####################################################

    @api.model
    def get_move_lines_for_reconciliation_widget(self, statement_line_id, partner_id=None, excluded_ids=None, str=False, offset=0, limit=None):
        """ Returns move lines for the bank statement reconciliation widget, formatted as a list of dicts
        """
        move_lines = self.get_move_lines_for_reconciliation(statement_line_id, partner_id=partner_id, excluded_ids=excluded_ids, str=str, offset=offset, limit=limit)

        statement_line = self.env['account.bank.statement.line'].browse(statement_line_id)
        target_currency = statement_line.currency_id or statement_line.journal_id.currency_id or statement_line.journal_id.company_id.currency_id

        return self.prepare_move_lines_for_reconciliation_widget(move_lines, target_currency=target_currency, target_date=statement_line.date)
    
    @api.model
    def get_move_lines_for_reconciliation(self, statement_line_id=None, partner_id=None, excluded_ids=None, str=False, offset=0, limit=None, additional_domain=None, overlook_partner=False):
        """ Return account.move.line records which can be used for bank statement reconciliation.
            :param statement_line_id:
            :param partner_id:
            :param excluded_ids:
            :param str:
            :param offset:
            :param limit:
            :param additional_domain:
            :param overlook_partner:
        """
        statement_line = self.env['account.bank.statement.line']
        if statement_line_id:
            statement_line.browse(statement_line_id)

        if partner_id is None:
            partner_id = statement_line.partner_id.id

        # Blue lines = payment on bank account not assigned to a statement yet
        reconciliation_aml_accounts = [statement_line.journal_id.default_credit_account_id.id, statement_line.journal_id.default_debit_account_id.id]
        domain_reconciliation = ['&', '&', ('statement_line_id', '=', False), ('account_id', 'in', reconciliation_aml_accounts), ('payment_id','<>', False)]

        # Black lines = unreconciled & (not linked to a payment or open balance created by statement
        domain_matching = [('reconciled', '=', False)]
        if partner_id or overlook_partner:
            domain_matching = expression.AND([domain_matching, [('account_id.internal_type', 'in', ['payable', 'receivable'])]])
        else:
            # TODO : find out what use case this permits (match a check payment, registered on a journal whose account type is other instead of liquidity)
            domain_matching = expression.AND([domain_matching, [('account_id.reconcile', '=', True)]])

        # Let's add what applies to both
        domain = expression.OR([domain_reconciliation, domain_matching])
        if partner_id and not overlook_partner:
            domain = expression.AND([domain, [('partner_id', '=', partner_id)]])

        # Domain factorized for all reconciliation use cases
        if str:
            str_domain = self.domain_move_lines_for_reconciliation(str=str)
            if not partner_id:
                str_domain = expression.OR([str_domain, ('partner_id.name', 'ilike', str)])
            domain = expression.AND([domain, str_domain])
        if excluded_ids:
            domain = expression.AND([[('id', 'not in', excluded_ids)], domain])

        # Domain from caller
        if additional_domain is None:
            additional_domain = []
        else:
            additional_domain = expression.normalize_domain(additional_domain)
        domain = expression.AND([domain, additional_domain])

        return self.env['account.move.line'].search(domain, offset=offset, limit=limit, order="date_maturity desc, id desc")

    @api.model
    def reconciliation_widget_auto_reconcile(self, statement_line_ids, num_already_reconciled_lines):
        automatic_reconciliation_entries = self.env['account.bank.statement.line']
        unreconciled = self.env['account.bank.statement.line']

        for stl in self.env['account.bank.statement.line'].browse(statement_line_ids):
            res = stl.auto_reconcile()
            if res:
                automatic_reconciliation_entries += stl
            else:
                unreconciled += stl

        # Collect various informations for the reconciliation widget
        notifications = []
        num_auto_reconciled = len(automatic_reconciliation_entries)
        if num_auto_reconciled > 0:
            auto_reconciled_message = num_auto_reconciled > 1 \
                and _("%d transactions were automatically reconciled.") % num_auto_reconciled \
                or _("1 transaction was automatically reconciled.")
            notifications += [{
                'type': 'info',
                'message': auto_reconciled_message,
                'details': {
                    'name': _("Automatically reconciled items"),
                    'model': 'account.move',
                    'ids': automatic_reconciliation_entries.mapped('journal_entry_ids').ids
                }
            }]
        return {
            'st_lines_ids': unreconciled.ids,
            'notifications': notifications,
            'statement_name': False,
            'num_already_reconciled_lines': num_auto_reconciled + num_already_reconciled_lines,
        }

    @api.model
    def get_data_for_reconciliation_widget(self, statement_line_ids, excluded_ids=None):
        """ Returns the data required to display a reconciliation widget, for each statement line """
        statement_lines = self.env['account.bank.statement.line'].browse(statement_line_ids)
        excluded_ids = excluded_ids or []
        ret = []

        for st_line in statement_lines:
            aml_recs = self.get_statement_line_reconciliation_proposition(st_line, excluded_ids=excluded_ids)
            target_currency = st_line.currency_id or st_line.journal_id.currency_id or st_line.journal_id.company_id.currency_id
            rp = self.prepare_move_lines_for_reconciliation_widget(aml_recs, target_currency=target_currency, target_date=st_line.date)
            excluded_ids += [move_line['id'] for move_line in rp]
            ret.append({
                'st_line': self.get_statement_line_for_reconciliation_widget(st_line),
                'reconciliation_proposition': rp
            })

        return ret

    @api.model
    def get_statement_line_reconciliation_proposition(self, statement_line, excluded_ids=None):
        """ Returns move lines that constitute the best guess to reconcile a statement line
            Note: it only looks for move lines in the same currency as the statement line.
        """
        if not excluded_ids:
            excluded_ids = []
        amount = statement_line.amount_currency or statement_line.amount
        company_currency = statement_line.journal_id.company_id.currency_id
        st_line_currency = statement_line.currency_id or statement_line.journal_id.currency_id
        currency = (st_line_currency and st_line_currency != company_currency) and st_line_currency.id or False
        precision = st_line_currency and st_line_currency.decimal_places or company_currency.decimal_places
        params = {'company_id': self.env.user.company_id.id,
                    'account_payable_receivable': (statement_line.journal_id.default_credit_account_id.id, statement_line.journal_id.default_debit_account_id.id),
                    'amount': float_round(amount, precision_digits=precision),
                    'partner_id': statement_line.partner_id.id,
                    'excluded_ids': tuple(excluded_ids),
                    'ref': statement_line.name,
                    }
        # Look for structured communication match
        if statement_line.name:
            add_to_select = ", CASE WHEN aml.ref = %(ref)s THEN 1 ELSE 2 END as temp_field_order "
            add_to_from = " JOIN account_move m ON m.id = aml.move_id "
            select_clause, from_clause, where_clause = statement_line._get_common_sql_query(overlook_partner=True, excluded_ids=excluded_ids, split=True)
            sql_query = select_clause + add_to_select + from_clause + add_to_from + where_clause
            sql_query += " AND (aml.ref= %(ref)s or m.name = %(ref)s) \
                    ORDER BY temp_field_order, date_maturity desc, aml.id desc"
            self.env.cr.execute(sql_query, params)
            results = self.env.cr.fetchone()
            if results:
                return self.env['account.move.line'].browse(results[0])

        # Look for a single move line with the same amount
        field = currency and 'amount_residual_currency' or 'amount_residual'
        liquidity_field = currency and 'amount_currency' or amount > 0 and 'debit' or 'credit'
        liquidity_amt_clause = currency and '%(amount)s' or 'abs(%(amount)s)'
        sql_query = statement_line._get_common_sql_query(excluded_ids=excluded_ids) + \
                " AND ("+field+" = %(amount)s OR (acc.internal_type = 'liquidity' AND "+liquidity_field+" = " + liquidity_amt_clause + ")) \
                ORDER BY date_maturity desc, aml.id desc LIMIT 1"
        self.env.cr.execute(sql_query, params)
        results = self.env.cr.fetchone()
        if results:
            return self.env['account.move.line'].browse(results[0])

        return self.env['account.move.line']

    @api.model
    def get_statement_line_for_reconciliation_widget(self, statement_line):
        """ Returns the data required by the bank statement reconciliation widget to display a statement line """

        statement_currency = statement_line.journal_id.currency_id or statement_line.journal_id.company_id.currency_id
        if statement_line.amount_currency and statement_line.currency_id:
            amount = statement_line.amount_currency
            amount_currency = statement_line.amount
            amount_currency_str = amount_currency > 0 and amount_currency or -amount_currency
            amount_currency_str = formatLang(self.env, amount_currency_str, currency_obj=statement_currency)
        else:
            amount = statement_line.amount
            amount_currency_str = ""
        amount_str = formatLang(self.env, abs(amount), currency_obj=statement_line.currency_id or statement_currency)

        data = {
            'id': statement_line.id,
            'ref': statement_line.ref,
            'note': statement_line.note or "",
            'name': statement_line.name,
            'date': statement_line.date,
            'amount': amount,
            'amount_str': amount_str,  # Amount in the statement line currency
            'currency_id': statement_line.currency_id.id or statement_currency.id,
            'partner_id': statement_line.partner_id.id,
            'journal_id': statement_line.journal_id.id,
            'statement_id': statement_line.statement_id.id,
            'account_id': [statement_line.journal_id.default_debit_account_id.id, statement_line.journal_id.default_debit_account_id.display_name],
            'account_code': statement_line.journal_id.default_debit_account_id.code,
            'account_name': statement_line.journal_id.default_debit_account_id.name,
            'partner_name': statement_line.partner_id.name,
            'communication_partner_name': statement_line.partner_name,
            'amount_currency_str': amount_currency_str,  # Amount in the statement currency
            'has_no_partner': not statement_line.partner_id.id,
        }
        if statement_line.partner_id:
            if amount > 0:
                data['open_balance_account_id'] = statement_line.partner_id.property_account_receivable_id.id
            else:
                data['open_balance_account_id'] = statement_line.partner_id.property_account_payable_id.id

        return data

    @api.multi
    def process_statement_line_reconciliations(self, statement_line_ids, data):
        """ Handles data sent from the bank statement reconciliation widget (and can otherwise serve as an old-API bridge)
            :param list on int: statement_ids
            :param list of dicts data: must contains the keys 'counterpart_aml_dicts', 'payment_aml_ids' and 'new_aml_dicts',
                whose value is the same as described in process_reconciliation except that ids are used instead of recordsets.
        """
        AccountMoveLine = self.env['account.move.line']
        statement_lines = self.env['account.bank.statement.line'].browse(statement_line_ids)

        for st_line, datum in pycompat.izip(statement_lines, data):
            payment_aml_rec = AccountMoveLine.browse(datum.get('payment_aml_ids', []))
            for aml_dict in datum.get('counterpart_aml_dicts', []):
                aml_dict['move_line'] = AccountMoveLine.browse(aml_dict['counterpart_aml_id'])
                del aml_dict['counterpart_aml_id']
            if datum.get('partner_id') is not None:
                st_line.write({'partner_id': datum['partner_id']})
            self.process_statement_line_reconciliation(st_line.id, datum.get('counterpart_aml_dicts', []), payment_aml_rec, datum.get('new_aml_dicts', []))

    @api.multi
    def process_statement_line_reconciliation(self, statement_line_id, counterpart_aml_dicts=None, payment_aml_rec=None, new_aml_dicts=None):
        statement_lines = self.env['account.bank.statement.line'].browse(statement_line_id)
        return statement_lines.process_reconciliation(counterpart_aml_dicts=counterpart_aml_dicts, payment_aml_rec=payment_aml_rec, new_aml_dicts=new_aml_dicts)

    ####################################################
    # account.move.line
    ####################################################

    @api.model
    def get_move_lines_for_manual_reconciliation(self, account_id, partner_id=False, excluded_ids=None, str=False, offset=0, limit=None, target_currency_id=False):
        """ Returns unreconciled move lines for an account or a partner+account, formatted for the manual reconciliation widget """
        domain = self._domain_move_lines_for_manual_reconciliation(account_id, partner_id, excluded_ids, str)
        lines = self.env['account.move.line'].search(domain, offset=offset, limit=limit, order="date_maturity desc, id desc")
        if target_currency_id:
            target_currency = self.env['res.currency'].browse(target_currency_id)
        else:
            account = self.env['account.account'].browse(account_id)
            target_currency = account.currency_id or account.company_id.currency_id
        return self.prepare_move_lines_for_reconciliation_widget(lines, target_currency=target_currency)
    
    @api.model
    def prepare_move_lines_for_reconciliation_widget(self, move_lines, target_currency=False, target_date=False):
        """ Returns move lines formatted for the manual/bank reconciliation widget
            :param target_currency: currency (Model or ID) you want the move line debit/credit converted into
            :param target_date: date to use for the monetary conversion
        """
        context = dict(self._context or {})
        ret = []

        if target_currency:
            # re-browse in case we were passed a currency ID via RPC call
            target_currency = self.env['res.currency'].browse(int(target_currency))

        for line in move_lines:
            company_currency = line.account_id.company_id.currency_id
            ret_line = {
                'id': line.id,
                'name': line.name != '/' and line.move_id.name + ': ' + line.name or line.move_id.name,
                'ref': line.move_id.ref or '',
                # For reconciliation between statement transactions and already registered payments (eg. checks)
                # NB : we don't use the 'reconciled' field because the line we're selecting is not the one that gets reconciled
                'account_id': [line.account_id.id, line.account_id.display_name],
                'already_paid': line.account_id.internal_type == 'liquidity',
                'account_code': line.account_id.code,
                'account_name': line.account_id.name,
                'account_type': line.account_id.internal_type,
                'date_maturity': line.date_maturity,
                'date': line.date,
                'journal_id': [line.journal_id.id, line.journal_id.display_name],
                'partner_id': line.partner_id.id,
                'partner_name': line.partner_id.name,
                'currency_id': (line.currency_id and line.amount_currency) and line.currency_id.id or False,
            }

            debit = line.debit
            credit = line.credit
            amount = line.amount_residual
            amount_currency = line.amount_residual_currency

            # For already reconciled lines, don't use amount_residual(_currency)
            if line.account_id.internal_type == 'liquidity':
                amount = abs(debit - credit)
                amount_currency = abs(line.amount_currency)

            # Get right debit / credit:
            target_currency = target_currency or company_currency
            line_currency = (line.currency_id and line.amount_currency) and line.currency_id or company_currency
            amount_currency_str = ""
            total_amount_currency_str = ""
            if line_currency != company_currency and target_currency == line_currency:
                # The payment currency is the invoice currency, but they are different than the company currency
                # We use the `amount_currency` computed during the invoice validation, at the invoice date
                # to avoid exchange gain/loss
                # e.g. an invoice of 100€ must be paid with 100€, whatever the company currency and the exchange rates
                total_amount = line.amount_currency
                actual_debit = debit > 0 and amount_currency or 0.0
                actual_credit = credit > 0 and -amount_currency or 0.0
                currency = line_currency
            else:
                # Either:
                #  - the invoice, payment, company currencies are all the same,
                #  - the payment currency is the company currency, but the invoice currency is different,
                #  - the invoice currency is the company currency, but the payment currency is different,
                #  - the invoice, payment and company currencies are all different.
                # For the two first cases, we can simply use the debit/credit of the invoice move line, which are always in the company currency,
                # and this is what the target need.
                # For the two last cases, we can use the debit/credit which are in the company currency, and then change them to the target currency
                total_amount = abs(debit - credit)
                actual_debit = debit > 0 and amount or 0.0
                actual_credit = credit > 0 and -amount or 0.0
                currency = company_currency
            if line_currency != target_currency:
                target_currency.compute(total_amount, line_currency)
                amount_currency_str = formatLang(self.env, target_currency.compute(abs(actual_debit or actual_credit), line_currency), currency_obj=line_currency)
                total_amount_currency_str = formatLang(self.env, target_currency.compute(total_amount, line_currency), currency_obj=line_currency)
            if currency != target_currency:
                ctx = context.copy()
                ctx.update({'date': target_date or line.date})
                total_amount = currency.with_context(ctx).compute(total_amount, target_currency)
                actual_debit = currency.with_context(ctx).compute(actual_debit, target_currency)
                actual_credit = currency.with_context(ctx).compute(actual_credit, target_currency)
            amount_str = formatLang(self.env, abs(actual_debit or actual_credit), currency_obj=target_currency)
            total_amount_str = formatLang(self.env, total_amount, currency_obj=target_currency)

            ret_line['debit'] = abs(actual_debit)
            ret_line['credit'] = abs(actual_credit)
            ret_line['amount_str'] = amount_str
            ret_line['total_amount_str'] = total_amount_str
            ret_line['amount_currency_str'] = amount_currency_str
            ret_line['total_amount_currency_str'] = total_amount_currency_str
            ret.append(ret_line)
        return ret

    @api.model
    def get_data_for_manual_reconciliation_widget(self, partner_ids, account_ids):
        """ Returns the data required for the invoices & payments matching of partners/accounts.
            If an argument is None, fetch all related reconciliations. Use [] to fetch nothing.
        """
        return {
            'customers': self.get_data_for_manual_reconciliation('partner', partner_ids, 'receivable'),
            'suppliers': self.get_data_for_manual_reconciliation('partner', partner_ids, 'payable'),
            'accounts': self.get_data_for_manual_reconciliation('account', account_ids),
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
        if res_ids is not None and len(res_ids) == 0:
            # Note : this short-circuiting is better for performances, but also required
            # since postgresql doesn't implement empty list (so 'AND id in ()' is useless)
            return []
        res_ids = res_ids and tuple(res_ids)

        assert res_type in ('partner', 'account')
        assert account_type in ('payable', 'receivable', None)
        is_partner = res_type == 'partner'
        res_alias = is_partner and 'p' or 'a'

        query = ("""
            SELECT {0} account_id, account_name, account_code, max_date,
                   to_char(last_time_entries_checked, 'YYYY-MM-DD') AS last_time_entries_checked
            FROM (
                    SELECT {1}
                        {res_alias}.last_time_entries_checked AS last_time_entries_checked,
                        a.id AS account_id,
                        a.name AS account_name,
                        a.code AS account_code,
                        MAX(l.write_date) AS max_date
                    FROM
                        account_move_line l
                        RIGHT JOIN account_account a ON (a.id = l.account_id)
                        RIGHT JOIN account_account_type at ON (at.id = a.user_type_id)
                        {2}
                    WHERE
                        a.reconcile IS TRUE
                        {3}
                        {4}
                        {5}
                        AND l.company_id = {6}
                        AND EXISTS (
                            SELECT NULL
                            FROM account_move_line l
                            WHERE l.account_id = a.id
                            {7}
                            AND l.amount_residual > 0
                        )
                        AND EXISTS (
                            SELECT NULL
                            FROM account_move_line l
                            WHERE l.account_id = a.id
                            {7}
                            AND l.amount_residual < 0
                        )
                    GROUP BY {8} a.id, a.name, a.code, {res_alias}.last_time_entries_checked
                    ORDER BY {res_alias}.last_time_entries_checked
                ) as s
            WHERE (last_time_entries_checked IS NULL OR max_date > last_time_entries_checked)
        """.format(
                is_partner and 'partner_id, partner_name,' or ' ',
                is_partner and 'p.id AS partner_id, p.name AS partner_name,' or ' ',
                is_partner and 'RIGHT JOIN res_partner p ON (l.partner_id = p.id)' or ' ',
                is_partner and ' ' or "AND at.type <> 'payable' AND at.type <> 'receivable'",
                account_type and "AND at.type = %(account_type)s" or '',
                res_ids and 'AND ' + res_alias + '.id in %(res_ids)s' or '',
                self.env.user.company_id.id,
                is_partner and 'AND l.partner_id = p.id' or ' ',
                is_partner and 'l.partner_id, p.id,' or ' ',
                res_alias=res_alias
            ))
        self.env.cr.execute(query, locals())

        # Apply ir_rules by filtering out
        rows = self.env.cr.dictfetchall()
        ids = [x['account_id'] for x in rows]
        allowed_ids = set(self.env['account.account'].browse(ids).ids)
        rows = [row for row in rows if row['account_id'] in allowed_ids]
        if is_partner:
            ids = [x['partner_id'] for x in rows]
            allowed_ids = set(self.env['res.partner'].browse(ids).ids)
            rows = [row for row in rows if row['partner_id'] in allowed_ids]

        # Fetch other data
        for row in rows:
            account = self.env['account.account'].browse(row['account_id'])
            row['currency_id'] = account.currency_id.id or account.company_id.currency_id.id
            partner_id = is_partner and row['partner_id'] or None
            row['reconciliation_proposition'] = self.get_move_lines_reconciliation_proposition(account.id, partner_id)
        return rows

    @api.model
    def get_move_lines_reconciliation_proposition(self, account_id, partner_id=False):
        """ Returns two lines whose amount are opposite """

        # Get pairs
        partner_id_condition = partner_id and 'AND a.partner_id = %(partner_id)s AND b.partner_id = %(partner_id)s' or ''
        query = """
                SELECT a.id, b.id
                FROM account_move_line a, account_move_line b
                WHERE a.amount_residual = -b.amount_residual
                AND NOT a.reconciled AND NOT b.reconciled
                AND a.account_id = %(account_id)s AND b.account_id = %(account_id)s
                {partner_id_condition}
                ORDER BY a.date desc
                LIMIT 10
            """.format(**locals())
        self.env.cr.execute(query, locals())
        pairs = self.env.cr.fetchall()

        # Apply ir_rules by filtering out
        all_pair_ids = [element for tupl in pairs for element in tupl]
        allowed_ids = set(self.env['account.move.line'].browse(all_pair_ids).ids)
        pairs = [pair for pair in pairs if pair[0] in allowed_ids and pair[1] in allowed_ids]

        # Return lines formatted
        if len(pairs) > 0:
            lines = self.env['account.move.line'].browse(list(pairs[0]))
            target_currency = (lines[0].currency_id and lines[0].amount_currency) and lines[0].currency_id or lines[0].company_id.currency_id
            return self.prepare_move_lines_for_reconciliation_widget(lines, target_currency=target_currency)
        return []

    @api.model
    def domain_move_lines_for_reconciliation(self, str):
        """ Returns the domain from the str search
            :param str: search string
        """
        if not str:
            return []
        str_domain = [
            '|', ('move_id.name', 'ilike', str),
            '|', ('move_id.ref', 'ilike', str),
            '|', ('date_maturity', 'like', str),
            '&', ('name', '!=', '/'), ('name', 'ilike', str)
        ]
        try:
            amount = float(str)
            amount_domain = [
                '|', ('amount_residual', '=', amount),
                '|', ('amount_residual_currency', '=', amount),
                '|', ('amount_residual', '=', -amount),
                '|', ('amount_residual_currency', '=', -amount),
                '&', ('account_id.internal_type', '=', 'liquidity'),
                '|', '|', ('debit', '=', amount), ('credit', '=', amount), ('amount_currency', '=', amount),
            ]
            str_domain = expression.OR([str_domain, amount_domain])
        except:
            pass
        return str_domain
    
    @api.model
    def _domain_move_lines_for_manual_reconciliation(self, account_id, partner_id=False, excluded_ids=None, str=False):
        """ Create domain criteria that are relevant to manual reconciliation. """
        domain = ['&', ('reconciled', '=', False), ('account_id', '=', account_id)]
        if partner_id:
            domain = expression.AND([domain, [('partner_id', '=', partner_id)]])
        if excluded_ids:
            domain = expression.AND([[('id', 'not in', excluded_ids)], domain])
        if str:
            str_domain = self.domain_move_lines_for_reconciliation(str=str)
            domain = expression.AND([domain, str_domain])
        return domain

    @api.model
    def process_move_line_reconciliations(self, data):
        """ Used to validate a batch of reconciliations in a single call
            :param data: list of dicts containing:
                - 'type': either 'partner' or 'account'
                - 'id': id of the affected res.partner or account.account
                - 'mv_line_ids': ids of exisiting account.move.line to reconcile
                - 'new_mv_line_dicts': list of dicts containing values suitable for account_move_line.create()
        """
        partner_ids = []
        account_ids = []
        for datum in data:
            if len(datum['mv_line_ids']) >= 1 or len(datum['mv_line_ids']) + len(datum['new_mv_line_dicts']) >= 2:
                self.process_move_line_reconciliation(datum['mv_line_ids'], datum['new_mv_line_dicts'])
            if datum['type'] == 'partner':
                partner_ids.append(datum['id'])
            if datum['type'] == 'account':
                account_ids.append(datum['id'])

        if partner_ids:
            self.env['res.partner'].mark_as_reconciled(partner_ids)
        if partner_ids:
            self.env['account.account'].mark_as_reconciled(account_ids)

    @api.model
    def process_move_line_reconciliation(self, mv_line_ids, new_mv_line_dicts):
        lines = self.env['account.move.line'].browse(mv_line_ids)
        return lines.process_reconciliation(new_mv_line_dicts)