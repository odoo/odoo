# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools import float_compare, float_is_zero
from odoo.exceptions import UserError


class AccountReconcileModel(models.Model):
    _name = 'account.reconcile.model'
    _description = 'Preset to create journal entries during a invoices and payments matching'
    _order = 'sequence, id'

    # Base fields.
    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(required=True, default=10)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)

    rule_type = fields.Selection(selection=[
        ('writeoff_button', _('Manually create a write-off on clicked button.')),
        ('writeoff_suggestion', _('Suggest counterpart values.')),
        ('invoice_matching', _('Match existing invoices/bills.'))
    ], string='Type', default='writeoff_button', required=True)
    auto_reconcile = fields.Boolean(string='Auto-validate',
        help='Validate the statement line automatically (reconciliation based on your rule).')

    # ===== Conditions =====
    match_journal_ids = fields.Many2many('account.journal', string='Journals',
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
        help='The reconciliation model will only be available from the selected journals.')
    match_nature = fields.Selection(selection=[
        ('amount_received', 'Amount Received'),
        ('amount_paid', 'Amount Paid'),
        ('both', 'Amount Paid/Received')
    ], string='Amount Nature', required=True, default='both',
        help='''The reconciliation model will only be applied to the selected transaction type:
        * Amount Received: Only applied when receiving an amount.
        * Amount Paid: Only applied when paying an amount.
        * Amount Paid/Received: Applied in both cases.''')
    match_amount = fields.Selection(selection=[
        ('lower', 'Is Lower Than'),
        ('greater', 'Is Greater Than'),
        ('between', 'Is Between'),
    ], string='Amount',
        help='The reconciliation model will only be applied when the amount being lower than, greater than or between specified amount(s).')
    match_amount_min = fields.Float(string='Amount Min Parameter')
    match_amount_max = fields.Float(string='Amount Max Parameter')
    match_label = fields.Selection(selection=[
        ('contains', 'Contains'),
        ('not_contains', 'Not Contains'),
        ('match_regex', 'Match Regex'),
    ], string='Label', help='''The reconciliation model will only be applied when the label:
        * Contains: The proposition label must contains this string (case insensitive).
        * Not Contains: Negation of "Contains".
        * Match Regex: Define your own regular expression.''')
    match_label_param = fields.Char(string='Label Parameter')
    match_same_currency = fields.Boolean(string='Same Currency Matching', default=True,
        help='Restrict to propositions having the same currency as the statement line.')
    match_total_amount = fields.Boolean(string='Amount Matching', default=True,
        help='The sum of total residual amount propositions matches the statement line amount.')
    match_total_amount_param = fields.Float(string='Amount Matching %', default=100,
        help='The sum of total residual amount propositions matches the statement line amount under this percentage.')
    match_partner = fields.Boolean(string='Partner Is Set',
        help='The reconciliation model will only be applied when a customer/vendor is set.')
    match_partner_ids = fields.Many2many('res.partner', string='Restrict Partners to',
        help='The reconciliation model will only be applied to the selected customers/vendors.')
    match_partner_category_ids = fields.Many2many('res.partner.category', string='Restrict Partner Categories to',
        help='The reconciliation model will only be applied to the selected customer/vendor categories.')

    # ===== Write-Off =====
    # First part fields.
    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade', domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")
    journal_id = fields.Many2one('account.journal', string='Journal', ondelete='cascade', help="This field is ignored in a bank statement reconciliation.", domain="[('company_id', '=', company_id)]")
    label = fields.Char(string='Journal Item Label')
    amount_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage of balance')
        ], required=True, default='percentage')
    is_tax_price_included = fields.Boolean(string='Is Tax Included in Price', related='tax_id.price_include',
        help='Technical field used inside the view to make the force_tax_included field readonly if the tax is already price included.')
    tax_amount_type = fields.Selection(string='Tax Amount Type', related='tax_id.amount_type',
        help='Technical field used inside the view to make the force_tax_included field invisible if the tax is a group.')
    force_tax_included = fields.Boolean(string='Tax Included in Price',
        help='Force the tax to be managed as a price included tax.')
    amount = fields.Float(string='Write-off Amount', digits=0, required=True, default=100.0, help="Fixed amount will count as a debit if it is negative, as a credit if it is positive.")
    tax_id = fields.Many2one('account.tax', string='Tax', ondelete='restrict', domain="[('company_id', '=', company_id)]")
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', ondelete='set null', domain="['|', ('company_id', '=', company_id), ('company_id', '=', False)]")
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags', domain="['|', ('company_id', '=', company_id), ('company_id', '=', False)]")

    # Second part fields.
    has_second_line = fields.Boolean(string='Add a second line', default=False)
    second_account_id = fields.Many2one('account.account', string='Second Account', ondelete='cascade', domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")
    second_journal_id = fields.Many2one('account.journal', string='Second Journal', ondelete='cascade', help="This field is ignored in a bank statement reconciliation.", domain="[('company_id', '=', company_id)]")
    second_label = fields.Char(string='Second Journal Item Label')
    second_amount_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage of amount')
        ], string="Second Amount type",required=True, default='percentage')
    is_second_tax_price_included = fields.Boolean(string='Is Second Tax Included in Price', related='second_tax_id.price_include',
        help='Technical field used inside the view to make the force_second_tax_included field readonly if the tax is already price included.')
    second_tax_amount_type = fields.Selection(string='Second Tax Amount Type', related='second_tax_id.amount_type',
        help='Technical field used inside the view to make the force_second_tax_included field invisible if the tax is a group.')
    force_second_tax_included = fields.Boolean(string='Second Tax Included in Price',
        help='Force the second tax to be managed as a price included tax.')
    second_amount = fields.Float(string='Second Write-off Amount', digits=0, required=True, default=100.0, help="Fixed amount will count as a debit if it is negative, as a credit if it is positive.")
    second_tax_id = fields.Many2one('account.tax', string='Second Tax', ondelete='restrict', domain="[('type_tax_use', '=', 'purchase'), ('company_id', '=', company_id)]")
    second_analytic_account_id = fields.Many2one('account.analytic.account', string='Second Analytic Account', ondelete='set null', domain="['|', ('company_id', '=', company_id), ('company_id', '=', False)]")
    second_analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Second Analytic Tags', domain="['|', ('company_id', '=', company_id), ('company_id', '=', False)]")

    @api.onchange('name')
    def onchange_name(self):
        self.label = self.name

    @api.onchange('tax_id')
    def _onchange_tax_id(self):
        if self.tax_id:
            self.force_tax_included = self.tax_id.price_include

    @api.onchange('second_tax_id')
    def _onchange_second_tax_id(self):
        if self.second_tax_id:
            self.force_second_tax_included = self.second_tax_id.price_include

    @api.onchange('match_total_amount_param')
    def _onchange_match_total_amount_param(self):
        if self.match_total_amount_param < 0 or self.match_total_amount_param > 100:
            self.match_total_amount_param = min(max(0, self.match_total_amount_param), 100)

    ####################################################
    # RECONCILIATION PROCESS
    ####################################################

    @api.model
    def _get_taxes_move_lines_dict(self, tax, base_line_dict):
        ''' Get move.lines dict (to be passed to the create()) corresponding to a tax.
        :param tax:             An account.tax record.
        :param base_line_dict:  A dict representing the move.line containing the base amount.
        :return: A list of dict representing move.lines to be created corresponding to the tax.
        '''
        balance = base_line_dict['debit'] - base_line_dict['credit']
        currency = base_line_dict.get('currency_id') and self.env['res.currency'].browse(base_line_dict['currency_id'])

        res = tax.compute_all(balance, currency=currency)

        new_aml_dicts = []
        for tax_res in res['taxes']:
            tax = self.env['account.tax'].browse(tax_res['id'])

            new_aml_dicts.append({
                'account_id': tax.account_id and tax.account_id.id or base_line_dict['account_id'],
                'name': tax.name,
                'partner_id': base_line_dict.get('partner_id'),
                'debit': tax_res['amount'] > 0 and tax_res['amount'] or 0,
                'credit': tax_res['amount'] < 0 and -tax_res['amount'] or 0,
                'analytic_account_id': tax.analytic and base_line_dict['analytic_account_id'],
                'analytic_tag_ids': tax.analytic and base_line_dict['analytic_tag_ids'],
                'tax_exigible': tax.tax_exigibility == 'on_payment',
                'tax_line_id': tax.id,
            })

            # Handle price included taxes.
            base_line_dict['debit'] = tax_res['base'] > 0 and tax_res['base'] or base_line_dict['debit']
            base_line_dict['credit'] = tax_res['base'] < 0 and -tax_res['base'] or base_line_dict['credit']
        return new_aml_dicts

    @api.multi
    def _get_write_off_move_lines_dict(self, st_line, move_lines=None):
        ''' Get move.lines dict (to be passed to the create()) corresponding to the reconciliation model's write-off lines.
        :param st_line:     An account.bank.statement.line record.
        :param move_lines:  An account.move.line recordset.
        :return: A list of dict representing move.lines to be created corresponding to the write-off lines.
        '''
        self.ensure_one()

        if self.rule_type == 'invoice_matching' and (not self.match_total_amount or (self.match_total_amount_param == 100)):
            return []

        line_residual = st_line.currency_id and st_line.amount_currency or st_line.amount
        line_currency = st_line.currency_id or st_line.journal_id.currency_id or st_line.company_id.currency_id
        total_residual = move_lines and sum(aml.currency_id and aml.amount_residual_currency or aml.amount_residual for aml in move_lines) or 0.0

        balance = total_residual - line_residual

        if not self.account_id or float_is_zero(balance, precision_rounding=line_currency.rounding):
            return []

        if self.amount_type == 'percentage':
            line_balance = balance * (self.amount / 100.0)
        else:
            line_balance = self.amount * (1 if balance > 0.0 else -1)

        new_aml_dicts = []

        # First write-off line.
        writeoff_line = {
            'name': self.label or st_line.name,
            'account_id': self.account_id.id,
            'analytic_account_id': self.analytic_account_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'debit': line_balance > 0 and line_balance or 0,
            'credit': line_balance < 0 and -line_balance or 0,
        }
        new_aml_dicts.append(writeoff_line)

        if self.tax_id:
            writeoff_line['tax_ids'] = [(6, None, [self.tax_id.id])]
            tax = self.tax_id
            if self.force_tax_included:
                tax = tax.with_context(force_price_include=True)
            new_aml_dicts += self._get_taxes_move_lines_dict(tax, writeoff_line)

        # Second write-off line.
        if self.has_second_line and self.second_account_id:
            remaining_balance = balance - sum(aml['debit'] - aml['credit'] for aml in new_aml_dicts)
            if self.second_amount_type == 'percentage':
                line_balance = remaining_balance * (self.second_amount / 100.0)
            else:
                line_balance = self.second_amount * (1 if remaining_balance > 0.0 else -1)
            second_writeoff_line = {
                'name': self.second_label or st_line.name,
                'account_id': self.second_account_id.id,
                'analytic_account_id': self.second_analytic_account_id.id,
                'analytic_tag_ids': [(6, 0, self.second_analytic_tag_ids.ids)],
                'debit': line_balance > 0 and line_balance or 0,
                'credit': line_balance < 0 and -line_balance or 0,
            }
            new_aml_dicts.append(second_writeoff_line)

            if self.second_tax_id:
                second_writeoff_line['tax_ids'] = [(6, None, [self.second_tax_id.id])]
                tax = self.second_tax_id
                if self.force_second_tax_included:
                    tax = tax.with_context(force_price_include=True)
                new_aml_dicts += self._get_taxes_move_lines_dict(tax, second_writeoff_line)

        return new_aml_dicts

    @api.multi
    def _prepare_reconciliation(self, st_line, move_lines=None, partner=None):
        ''' Reconcile the statement line with some move lines using this reconciliation model.
        :param st_line:     An account.bank.statement.line record.
        :param move_lines:  An account.move.line recordset.
        :param partner_id:  An optional res.partner record. If not set, st_line.partner_id will be used.
        :return:            Counterpart account.moves.
        '''
        self.ensure_one()

        # Create counterpart_aml_dicts + payment_aml_rec.
        counterpart_aml_dicts = []
        payment_aml_rec = self.env['account.move.line']
        if move_lines:
            for aml in move_lines:
                if aml.account_id.internal_type == 'liquidity':
                    payment_aml_rec |= aml
                else:
                    amount = aml.currency_id and aml.amount_residual_currency or aml.amount_residual
                    counterpart_aml_dicts.append({
                        'name': aml.name if aml.name != '/' else aml.move_id.name,
                        'debit': amount < 0 and -amount or 0,
                        'credit': amount > 0 and amount or 0,
                        'move_line': aml,
                    })

        # Create new_aml_dicts.
        new_aml_dicts = self._get_write_off_move_lines_dict(st_line, move_lines=move_lines)

        line_residual = st_line.currency_id and st_line.amount_currency or st_line.amount
        line_currency = st_line.currency_id or st_line.journal_id.currency_id or st_line.company_id.currency_id
        total_residual = move_lines and sum(aml.currency_id and aml.amount_residual_currency or aml.amount_residual for aml in move_lines) or 0.0
        total_residual -= sum(aml['debit'] - aml['credit'] for aml in new_aml_dicts)

        # Create open_balance_dict
        open_balance_dict = None
        if float_compare(line_residual, total_residual, precision_rounding=line_currency.rounding) != 0:
            if not partner and not st_line.partner_id:
                open_balance_dict = False
            else:
                balance = total_residual - line_residual
                partner = partner or st_line.partner_id
                open_balance_dict = {
                    'name': '%s : %s' % (st_line.name, _('Open Balance')),
                    'account_id': balance < 0 and partner.property_account_payable_id.id or partner.property_account_receivable_id.id,
                    'debit': balance > 0 and balance or 0,
                    'credit': balance < 0 and -balance or 0,
                }
        return {
           'counterpart_aml_dicts': counterpart_aml_dicts,
           'payment_aml_rec': payment_aml_rec,
           'new_aml_dicts': new_aml_dicts,
           'open_balance_dict': open_balance_dict
        }

    ####################################################
    # RECONCILIATION CRITERIA
    ####################################################

    @api.multi
    def _apply_conditions(self, query, params):
        self.ensure_one()
        rule = self
        # Filter on journals.
        if rule.match_journal_ids:
            query += ' AND st_line.journal_id IN %s'
            params += [tuple(rule.match_journal_ids.ids)]

        # Filter on amount nature.
        if rule.match_nature == 'amount_received':
            query += ' AND st_line.amount >= 0.0'
        elif rule.match_nature == 'amount_paid':
            query += ' AND st_line.amount <= 0.0'

        # Filter on amount.
        if rule.match_amount:
            query += ' AND ROUND(ABS(st_line.amount), jnl_precision.dp) '
            if rule.match_amount == 'lower':
                query += '< %s'
                params += [self.match_amount_max]
            elif rule.match_amount == 'greater':
                query += '> %s'
                params += [self.match_amount_min]
            else:
                # if self.match_amount == 'between'
                query += 'BETWEEN %s AND %s'
                params += [rule.match_amount_min, rule.match_amount_max]

        # Filter on label.
        if rule.match_label == 'contains':
            query += ' AND st_line.name ILIKE %s'
            params += ['%%%s%%' % rule.match_label_param]
        elif rule.match_label == 'not_contains':
            query += ' AND st_line.name NOT ILIKE %s'
            params += ['%%%s%%' % rule.match_label_param]
        elif rule.match_label == 'match_regex':
            query += ' AND st_line.name ~* %s'
            params += [rule.match_label_param]

        # Filter on partners.
        if rule.match_partner:
            query += ' AND line_partner.partner_id != 0'

            if rule.match_partner_ids:
                query += ' AND line_partner.partner_id IN %s'
                params += [tuple(rule.match_partner_ids.ids)]

            if rule.match_partner_category_ids:
                query += '''
                    AND line_partner.partner_id IN (
                        SELECT DISTINCT categ.partner_id FROM res_partner_res_partner_category_rel categ WHERE categ.category_id IN %s
                    )
                '''
                params += [tuple(rule.match_partner_category_ids.ids)]

        return query, params

    @api.multi
    def _get_with_tables(self, st_lines, partner_map=None):
        with_tables = '''
            WITH jnl_precision AS (
                SELECT
                    j.id AS journal_id, currency.decimal_places AS dp
                FROM account_journal j
                LEFT JOIN res_company c ON j.company_id = c.id
                LEFT JOIN res_currency currency ON COALESCE(j.currency_id, c.currency_id) = currency.id
                WHERE j.type IN ('bank', 'cash')
            )'''
        # Compute partners values table.
        # This is required since some statement line's partners could be shadowed in the reconciliation widget.
        partners_list = []
        for line in st_lines:
            partner_id = partner_map and partner_map.get(line.id) or line.partner_id.id or 0
            partners_list.append('(%d, %d)' % (line.id, partner_id))
        partners_table = 'SELECT * FROM (VALUES %s) AS line_partner (line_id, partner_id)' % ','.join(partners_list)
        with_tables += ', partners_table AS (' + partners_table + ')'
        return with_tables

    @api.multi
    def _get_invoice_matching_query(self, st_lines, excluded_ids=None, partner_map=None):
        ''' Get the query applying all rules trying to match existing entries with the given statement lines.
        :param st_lines:        Account.bank.statement.lines recordset.
        :param excluded_ids:    Account.move.lines to exclude.
        :param partner_map:     Dict mapping each line with new partner eventually.
        :return:                (query, params)
        '''
        if any(m.rule_type != 'invoice_matching' for m in self):
            raise UserError(_('Programmation Error: Can\'t call _get_invoice_matching_query() for different rules than \'invoice_matching\''))

        queries = []
        all_params = []
        for rule in self:
            # N.B: 'communication_flag' is there to distinguish invoice matching through the number/reference
            # (higher priority) from invoice matching using the partner (lower priority).
            query = '''
            SELECT
                %s                                  AS sequence,
                %s                                  AS model_id,
                st_line.id                          AS id,
                aml.id                              AS aml_id,
                aml.currency_id                     AS aml_currency_id,
                aml.date_maturity                   AS aml_date_maturity,
                aml.amount_residual                 AS aml_amount_residual,
                aml.amount_residual_currency        AS aml_amount_residual_currency,
                aml.balance                         AS aml_balance,
                aml.amount_currency                 AS aml_amount_currency,
                account.internal_type               AS account_internal_type,

                -- Determine a matching or not with the statement line communication using the move.name or move.ref.
                -- only digits are considered and reference are split by any space characters
                regexp_split_to_array(substring(REGEXP_REPLACE(move.name, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*'), '\s+')
                && regexp_split_to_array(substring(REGEXP_REPLACE(st_line.name, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*'), '\s+')
                OR
                (
                    move.ref IS NOT NULL
                    AND
                        regexp_split_to_array(substring(REGEXP_REPLACE(move.ref, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*'), '\s+')
                        &&
                        regexp_split_to_array(substring(REGEXP_REPLACE(st_line.name, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*'), '\s+')
                )                                   AS communication_flag
            FROM account_bank_statement_line st_line
            LEFT JOIN account_journal journal       ON journal.id = st_line.journal_id
            LEFT JOIN jnl_precision                 ON jnl_precision.journal_id = journal.id
            LEFT JOIN res_company company           ON company.id = st_line.company_id
            LEFT JOIN partners_table line_partner   ON line_partner.line_id = st_line.id
            , account_move_line aml
            LEFT JOIN account_move move             ON move.id = aml.move_id
            LEFT JOIN account_account account       ON account.id = aml.account_id
            WHERE st_line.id IN %s
                AND aml.company_id = st_line.company_id
                AND (
                        -- the field match_partner of the rule might enforce the second part of
                        -- the OR condition, later in _apply_conditions()
                        line_partner.partner_id = 0
                        OR
                        aml.partner_id = line_partner.partner_id
                    )
                AND CASE WHEN st_line.amount > 0.0
                         THEN aml.balance > 0
                         ELSE aml.balance < 0
                    END

                -- if there is a partner, propose all aml of the partner, otherwise propose only the ones
                -- matching the statement line communication
                -- "case when" used to enforce evaluation order (performance optimization)
                AND (CASE WHEN
                (
                    (
                    -- blue lines appearance conditions
                    aml.account_id IN (journal.default_credit_account_id, journal.default_debit_account_id)
                    AND aml.statement_id IS NULL
                    AND (
                        company.account_bank_reconciliation_start IS NULL
                        OR
                        aml.date > company.account_bank_reconciliation_start
                        )
                    )
                    OR
                    (
                    -- black lines appearance conditions
                    account.reconcile IS TRUE
                    AND aml.reconciled IS FALSE
                    )
                )
                THEN ( CASE WHEN
                (
                    (
                        line_partner.partner_id != 0
                        AND
                        aml.partner_id = line_partner.partner_id
                    )
                    OR
                    (
                        line_partner.partner_id = 0
                        AND
                        substring(REGEXP_REPLACE(st_line.name, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*') != ''
                        AND
                        (
                            regexp_split_to_array(substring(REGEXP_REPLACE(move.name, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*'), '\s+')
                            &&
                            regexp_split_to_array(substring(REGEXP_REPLACE(st_line.name, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*'), '\s+')
                            OR
                            (
                                move.ref IS NOT NULL
                                AND
                                    regexp_split_to_array(substring(REGEXP_REPLACE(move.ref, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*'), '\s+')
                                    &&
                                    regexp_split_to_array(substring(REGEXP_REPLACE(st_line.name, '[^0-9|^\s]', '', 'g'), '\S(?:.*\S)*'), '\s+')
                            )
                        )
                    )
                )
                THEN 1 END) END) = 1
            '''
            # Filter on the same currency.
            if rule.match_same_currency:
                query += '''
                    AND COALESCE(st_line.currency_id, journal.currency_id, company.currency_id) = COALESCE(aml.currency_id, company.currency_id)
                '''

            params = [rule.sequence, rule.id, tuple(st_lines.ids)]
            # Filter out excluded account.move.line.
            if excluded_ids:
                query += 'AND aml.id NOT IN %s'
                params += [tuple(excluded_ids)]
            query, params = rule._apply_conditions(query, params)
            queries.append(query)
            all_params += params
        full_query = self._get_with_tables(st_lines, partner_map=partner_map)
        full_query += ' UNION ALL '.join(queries)
        # Oldest due dates come first.
        full_query += ' ORDER BY aml_date_maturity, aml_id'
        return full_query, all_params

    @api.multi
    def _get_writeoff_suggestion_query(self, st_lines, excluded_ids=None, partner_map=None):
        ''' Get the query applying all reconciliation rules.
        :param st_lines:        Account.bank.statement.lines recordset.
        :param excluded_ids:    Account.move.lines to exclude.
        :param partner_map:     Dict mapping each line with new partner eventually.
        :return:                (query, params)
        '''
        if any(m.rule_type != 'writeoff_suggestion' for m in self):
            raise UserError(_('Programmation Error: Can\'t call _get_wo_suggestion_query() for different rules than \'writeoff_suggestion\''))

        queries = []
        all_params = []
        for rule in self:
            query = '''
                SELECT
                    %s                                  AS sequence,
                    %s                                  AS model_id,
                    st_line.id                          AS id
                FROM account_bank_statement_line st_line
                LEFT JOIN account_journal journal       ON journal.id = st_line.journal_id
                LEFT JOIN jnl_precision                 ON jnl_precision.journal_id = journal.id
                LEFT JOIN res_company company           ON company.id = st_line.company_id
                LEFT JOIN partners_table line_partner   ON line_partner.line_id = st_line.id
                WHERE st_line.id IN %s
            '''
            params = [rule.sequence, rule.id, tuple(st_lines.ids)]

            query, params = rule._apply_conditions(query, params)
            queries.append(query)
            all_params += params

        full_query = self._get_with_tables(st_lines, partner_map=partner_map)
        full_query += ' UNION ALL '.join(queries)
        return full_query, all_params

    @api.multi
    def _check_rule_propositions(self, statement_line, candidates):
        ''' Check restrictions that can't be handled for each move.line separately.
        /!\ Only used by models having a type equals to 'invoice_matching'.
        :param statement_line:  An account.bank.statement.line record.
        :param candidates:      Fetched account.move.lines from query (dict).
        :return:                True if the reconciliation propositions are accepted. False otherwise.
        '''
        if not self.match_total_amount:
            return True
        if not candidates:
            return False

        # Match total residual amount.
        total_residual = 0.0
        for aml in candidates:
            if aml['account_internal_type'] == 'liquidity':
                total_residual += aml['aml_currency_id'] and aml['aml_amount_currency'] or aml['aml_balance']
            else:
                total_residual += aml['aml_currency_id'] and aml['aml_amount_residual_currency'] or aml['aml_amount_residual']
        line_residual = statement_line.currency_id and statement_line.amount_currency or statement_line.amount
        line_currency = statement_line.currency_id or statement_line.journal_id.currency_id or statement_line.company_id.currency_id

        # Statement line amount is equal to the total residual.
        if float_is_zero(total_residual - line_residual, precision_rounding=line_currency.rounding):
            return True

        line_residual_to_compare = line_residual if line_residual > 0.0 else -line_residual
        total_residual_to_compare = total_residual if line_residual > 0.0 else -total_residual

        if line_residual_to_compare > total_residual_to_compare:
            amount_percentage = (total_residual_to_compare / line_residual_to_compare) * 100
        elif total_residual:
            amount_percentage = (line_residual_to_compare / total_residual_to_compare) * 100
        else:
            return False
        return amount_percentage >= self.match_total_amount_param

    @api.multi
    def _apply_rules(self, st_lines, excluded_ids=None, partner_map=None):
        ''' Apply criteria to get candidates for all reconciliation models.
        :param st_lines:        Account.bank.statement.lines recordset.
        :param excluded_ids:    Account.move.lines to exclude.
        :param partner_map:     Dict mapping each line with new partner eventually.
        :return:                A dict mapping each statement line id with:
            * aml_ids:      A list of account.move.line ids.
            * model:        An account.reconcile.model record (optional).
            * status:       'reconciled' if the lines has been already reconciled, 'write_off' if the write-off must be
                            applied on the statement line.
        '''
        available_models = self.filtered(lambda m: m.rule_type != 'writeoff_button')

        results = dict((r.id, {'aml_ids': []}) for r in st_lines)

        if not available_models:
            return results

        ordered_models = available_models.sorted(key=lambda m: (m.sequence, m.id))

        grouped_candidates = {}

        # Type == 'invoice_matching'.
        # Map each (st_line.id, model_id) with matching amls.
        invoices_models = ordered_models.filtered(lambda m: m.rule_type == 'invoice_matching')
        if invoices_models:
            query, params = invoices_models._get_invoice_matching_query(st_lines, excluded_ids=excluded_ids, partner_map=partner_map)
            self._cr.execute(query, params)
            query_res = self._cr.dictfetchall()

            for res in query_res:
                grouped_candidates.setdefault(res['id'], {})
                grouped_candidates[res['id']].setdefault(res['model_id'], [])
                grouped_candidates[res['id']][res['model_id']].append(res)

        # Type == 'writeoff_suggestion'.
        # Map each (st_line.id, model_id) with a flag indicating the st_line matches the criteria.
        write_off_models = ordered_models.filtered(lambda m: m.rule_type == 'writeoff_suggestion')
        if write_off_models:
            query, params = write_off_models._get_writeoff_suggestion_query(st_lines, excluded_ids=excluded_ids, partner_map=partner_map)
            self._cr.execute(query, params)
            query_res = self._cr.dictfetchall()

            for res in query_res:
                grouped_candidates.setdefault(res['id'], {})
                grouped_candidates[res['id']].setdefault(res['model_id'], True)

        # Keep track of already processed amls.
        amls_ids_to_exclude = set()

        # Keep track of already reconciled amls.
        reconciled_amls_ids = set()

        # Iterate all and create results.
        for line in st_lines:
            line_currency = line.currency_id or line.journal_id.currency_id or line.company_id.currency_id
            line_residual = line.currency_id and line.amount_currency or line.amount

            # Search for applicable rule.
            # /!\ BREAK are very important here to avoid applying multiple rules on the same line.
            for model in ordered_models:
                # No result found.
                if not grouped_candidates.get(line.id) or not grouped_candidates[line.id].get(model.id):
                    continue

                excluded_lines_found = False

                if model.rule_type == 'invoice_matching':
                    candidates = grouped_candidates[line.id][model.id]

                    # If some invoices match on the communication, suggest them.
                    # Otherwise, suggest all invoices having the same partner.
                    # N.B: The only way to match a line without a partner is through the communication.
                    first_batch_candidates = []
                    second_batch_candidates = []
                    for c in candidates:
                        # Don't take into account already reconciled lines.
                        if c['aml_id'] in reconciled_amls_ids:
                            continue

                        # Dispatch candidates between lines matching invoices with the communication or only the partner.
                        if c['communication_flag']:
                            first_batch_candidates.append(c)
                        elif not first_batch_candidates:
                            second_batch_candidates.append(c)
                    available_candidates = first_batch_candidates or second_batch_candidates

                    # Special case: the amount are the same, submit the line directly.
                    for c in available_candidates:
                        residual_amount = c['aml_currency_id'] and c['aml_amount_residual_currency'] or c['aml_amount_residual']

                        if float_is_zero(residual_amount - line_residual, precision_rounding=line_currency.rounding):
                            available_candidates = [c]
                            break

                    # Needed to handle check on total residual amounts.
                    if first_batch_candidates or model._check_rule_propositions(line, available_candidates):
                        results[line.id]['model'] = model

                        # Add candidates to the result.
                        for candidate in available_candidates:

                            # Special case: the propositions match the rule but some of them are already consumed by
                            # another one. Then, suggest the remaining propositions to the user but don't make any
                            # automatic reconciliation.
                            if candidate['aml_id'] in amls_ids_to_exclude:
                                excluded_lines_found = True
                                continue

                            results[line.id]['aml_ids'].append(candidate['aml_id'])
                            amls_ids_to_exclude.add(candidate['aml_id'])

                        if excluded_lines_found:
                            break

                        # Create write-off lines.
                        move_lines = self.env['account.move.line'].browse(results[line.id]['aml_ids'])
                        partner = partner_map and partner_map.get(line.id) and self.env['res.partner'].browse(partner_map[line.id])
                        reconciliation_results = model._prepare_reconciliation(line, move_lines, partner=partner)

                        # A write-off must be applied.
                        if reconciliation_results['new_aml_dicts']:
                            results[line.id]['status'] = 'write_off'

                        # Process auto-reconciliation.
                        if model.auto_reconcile:
                            # An open balance is needed but no partner has been found.
                            if reconciliation_results['open_balance_dict'] is False:
                                break

                            new_aml_dicts = reconciliation_results['new_aml_dicts']
                            if reconciliation_results['open_balance_dict']:
                                new_aml_dicts.append(reconciliation_results['open_balance_dict'])
                            if not line.partner_id and partner:
                                line.partner_id = partner
                            counterpart_moves = line.process_reconciliation(
                                counterpart_aml_dicts=reconciliation_results['counterpart_aml_dicts'],
                                payment_aml_rec=reconciliation_results['payment_aml_rec'],
                                new_aml_dicts=new_aml_dicts,
                            )
                            results[line.id]['status'] = 'reconciled'
                            results[line.id]['reconciled_lines'] = counterpart_moves.mapped('line_ids')

                            # The reconciled move lines are no longer candidates for another rule.
                            reconciled_amls_ids.update(move_lines.ids)

                        # Break models loop.
                        break

                elif model.rule_type == 'writeoff_suggestion' and grouped_candidates[line.id][model.id]:
                    results[line.id]['model'] = model
                    results[line.id]['status'] = 'write_off'

                    # Create write-off lines.
                    partner = partner_map and partner_map.get(line.id) and self.env['res.partner'].browse(partner_map[line.id])
                    reconciliation_results = model._prepare_reconciliation(line, partner=partner)

                    # An open balance is needed but no partner has been found.
                    if reconciliation_results['open_balance_dict'] is False:
                        break

                    # Process auto-reconciliation.
                    if model.auto_reconcile:
                        new_aml_dicts = reconciliation_results['new_aml_dicts']
                        if reconciliation_results['open_balance_dict']:
                            new_aml_dicts.append(reconciliation_results['open_balance_dict'])
                        if not line.partner_id and partner:
                            line.partner_id = partner
                        counterpart_moves = line.process_reconciliation(
                            counterpart_aml_dicts=reconciliation_results['counterpart_aml_dicts'],
                            payment_aml_rec=reconciliation_results['payment_aml_rec'],
                            new_aml_dicts=new_aml_dicts,
                        )
                        results[line.id]['status'] = 'reconciled'
                        results[line.id]['reconciled_lines'] = counterpart_moves.mapped('line_ids')

                    # Break models loop.
                    break
        return results
