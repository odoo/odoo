from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FsGeneralLedger(models.AbstractModel):
    _name = 'fs.general.ledger'
    _description = 'Community General Ledger'

    @api.model
    def _aml_base_domain(self, options):
        domain = [
            ('company_id', 'in', options['company_ids']),
            ('display_type', 'not in', ('line_section', 'line_subsection', 'line_note')),
        ]
        if options.get('target_move', 'posted') == 'posted':
            domain.append(('parent_state', '=', 'posted'))
        else:
            domain.append(('parent_state', '!=', 'cancel'))
        if options.get('journal_ids'):
            domain.append(('journal_id', 'in', options['journal_ids']))
        return domain

    @api.model
    def _account_domain(self, options):
        domain = [('company_ids', 'in', options['company_ids'])]
        if options.get('account_ids'):
            domain.append(('id', 'in', options['account_ids']))
            return domain
        filter_accounts = (options.get('filter_accounts') or '').strip()
        if filter_accounts:
            domain += ['|', ('code', '=ilike', f'{filter_accounts}%'), ('name', 'ilike', filter_accounts)]
        return domain

    @api.model
    def _init_balance_domain(self, account, options):
        """Enterprise: opening balance before date_from (P&amp;L only within fiscal year)."""
        date_from = fields.Date.to_date(options['date_from'])
        domain = self._aml_base_domain(options) + [
            ('account_id', '=', account.id),
            ('date', '<', date_from),
        ]
        if not account.include_initial_balance:
            company = self.env['res.company'].browse(options['company_ids'][0])
            fy_start = company.compute_fiscalyear_dates(date_from)['date_from']
            domain.append(('date', '>=', fy_start))
        return domain

    @api.model
    def _period_domain(self, account, options):
        return self._aml_base_domain(options) + [
            ('account_id', '=', account.id),
            ('date', '>=', options['date_from']),
            ('date', '<=', options['date_to']),
        ]

    @api.model
    def _sum_debit_credit(self, domain):
        MoveLine = self.env['account.move.line']
        rows = MoveLine._read_group(domain, aggregates=['debit:sum', 'credit:sum'])
        debit = rows[0][0] or 0.0
        credit = rows[0][1] or 0.0
        return debit, credit, debit - credit

    @api.model
    def get_report_data(self, options):
        self = self.with_context(allowed_company_ids=options['company_ids'])
        Account = self.env['account.account']
        MoveLine = self.env['account.move.line']
        currency = self.env['res.company'].browse(options['company_ids'][0]).currency_id
        unfolded = set(options.get('unfolded_account_ids') or [])
        accounts = Account.search(self._account_domain(options), order='code, name')
        lines = []
        for account in accounts:
            init_debit, init_credit, init_balance = self._sum_debit_credit(
                self._init_balance_domain(account, options)
            )
            period_debit, period_credit, period_balance = self._sum_debit_credit(
                self._period_domain(account, options)
            )
            debit = currency.round(init_debit + period_debit)
            credit = currency.round(init_credit + period_credit)
            balance = currency.round(init_balance + period_balance)
            if currency.is_zero(debit) and currency.is_zero(credit) and currency.is_zero(balance):
                continue
            is_unfolded = account.id in unfolded
            account_line = {
                'id': f'account-{account.id}',
                'account_id': account.id,
                'name': account.display_name,
                'level': 1,
                'unfoldable': True,
                'unfolded': is_unfolded,
                'kind': 'account',
                'date': False,
                'partner_name': '',
                'amount_currency': False,
                'debit': debit,
                'credit': credit,
                'balance': balance,
                'children': [],
            }
            if is_unfolded:
                running = 0.0
                if not currency.is_zero(init_debit) or not currency.is_zero(init_credit) or not currency.is_zero(init_balance):
                    running = currency.round(init_balance)
                    account_line['children'].append({
                        'id': f'init-{account.id}',
                        'account_id': account.id,
                        'name': _('Initial Balance'),
                        'level': 3,
                        'unfoldable': False,
                        'unfolded': False,
                        'kind': 'initial',
                        'date': False,
                        'partner_name': '',
                        'amount_currency': False,
                        'debit': currency.round(init_debit),
                        'credit': currency.round(init_credit),
                        'balance': running,
                    })
                amls = MoveLine.search(
                    self._period_domain(account, options),
                    order='date, id',
                )
                for aml in amls:
                    running = currency.round(running + aml.balance)
                    amount_currency = False
                    if aml.currency_id and aml.currency_id != currency and not aml.currency_id.is_zero(aml.amount_currency):
                        amount_currency = aml.amount_currency
                    account_line['children'].append({
                        'id': f'aml-{aml.id}',
                        'account_id': account.id,
                        'aml_id': aml.id,
                        'move_id': aml.move_id.id,
                        'name': aml.move_name or aml.name or '',
                        'level': 3,
                        'unfoldable': False,
                        'unfolded': False,
                        'kind': 'aml',
                        'date': fields.Date.to_string(aml.date),
                        'partner_name': aml.partner_id.display_name if aml.partner_id else '',
                        'amount_currency': amount_currency,
                        'currency_id': aml.currency_id.id if amount_currency is not False else False,
                        'debit': aml.debit,
                        'credit': aml.credit,
                        'balance': running,
                    })
            lines.append(account_line)
        return {
            'lines': lines,
            'currency_id': currency.id,
            'has_unposted': bool(MoveLine.search_count(
                self._aml_base_domain({**options, 'target_move': 'all'}) + [
                    ('parent_state', '=', 'draft'),
                    ('date', '<=', options['date_to']),
                ],
                limit=1,
            )),
        }

    @api.model
    def open_unposted_moves(self, options):
        """Open draft journal entries that might impact the reporting (Enterprise)."""
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_journal_line')
        action['domain'] = [
            ('state', '=', 'draft'),
            ('date', '<=', options['date_to']),
            ('company_id', 'in', options.get('company_ids') or []),
        ]
        action['context'] = {}
        return action

    @api.model
    def caret_option_open_general_ledger(self, options, params):
        """Mirror Enterprise: open GL client action filtered on the account."""
        account_id = params.get('account_id')
        if not account_id:
            raise UserError(_(
                "'Open General Ledger' caret option is only available from report lines "
                "targeting accounts."
            ))
        account = self.env['account.account'].browse(account_id)
        column = options['columns'][-1]
        date_to = fields.Date.to_date(column['date_to'])
        company = self.env['res.company'].browse(options['company_ids'][0])
        if column.get('date_from'):
            date_from = fields.Date.to_date(column['date_from'])
        else:
            date_from = company.compute_fiscalyear_dates(date_to)['date_from']
        date_opts = options.get('date') or {}
        gl_options = {
            'company_ids': options['company_ids'],
            'date_from': fields.Date.to_string(date_from),
            'date_to': fields.Date.to_string(date_to),
            'period_type': date_opts.get('period_type') or (
                'custom' if column.get('date_from') else 'year'
            ),
            'target_move': options.get('target_move', 'posted'),
            'journal_ids': options.get('journal_ids') or [],
            'filter_accounts': account.code or account.name or '',
            'account_ids': [account.id],
            'unfolded_account_ids': [account.id],
        }
        action = self.env['ir.actions.actions']._for_xml_id(
            'account_fs_report.action_fs_general_ledger'
        )
        action['params'] = {
            'options': gl_options,
            'ignore_session': True,
        }
        action['context'] = {
            **dict(self.env.context),
            'default_filter_accounts': account.code or '',
        }
        return action

    @api.model
    def _journal_items_action(self, options, params=None):
        """Mirror Enterprise account.report.open_journal_items (search defaults + views).

        params keys: account_id, group_by_account, view_ref, extra_domain, name
        """
        params = params or {}
        date_opts = options.get('date') or {}
        date_from = date_opts.get('date_from') or options.get('date_from') or False
        date_to = date_opts.get('date_to') or options.get('date_to')
        if not date_to and options.get('columns'):
            date_to = options['columns'][-1].get('date_to')
            date_from = date_from or options['columns'][-1].get('date_from') or False

        posted = options.get('target_move', 'posted') == 'posted' and not options.get('all_entries')
        ctx = {
            **dict(self.env.context),
            'active_test': False,
            'create': 0,
            'search_default_group_by_account': 1 if params.get('group_by_account') else 0,
            'search_default_posted': 1 if posted else 0,
            'date_from': date_from or False,
            'date_to': date_to,
            'expand': 1,
        }
        if date_from:
            ctx['search_default_date_between'] = 1
        else:
            ctx['search_default_date_before'] = 1

        action_domain = [
            ('display_type', 'not in', ('line_section', 'line_subsection', 'line_note')),
            ('parent_state', '!=', 'cancel'),
        ]
        company_ids = options.get('company_ids')
        if company_ids:
            action_domain.append(('company_id', 'in', company_ids))
        journal_ids = options.get('journal_ids') or []
        if journal_ids:
            if len(journal_ids) == 1:
                ctx['search_default_journal_id'] = journal_ids
            else:
                ctx['search_default_journal_ids'] = True
                ctx['journal_ids'] = journal_ids

        account_id = params.get('account_id')
        if account_id:
            ctx['active_id'] = account_id
            ctx['search_default_account_id'] = [account_id]

        extra_domain = params.get('extra_domain') or []
        if extra_domain:
            action_domain = action_domain + list(extra_domain)

        view_id = False
        view_ref = params.get('view_ref')
        if view_ref:
            view_id = self.env.ref(view_ref).id

        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all')
        action.update({
            'name': params.get('name') or _('Journal Items'),
            'domain': action_domain,
            'view_mode': 'list,pivot,graph,kanban',
            'views': [
                (view_id, 'list'),
                (False, 'pivot'),
                (False, 'graph'),
                (False, 'kanban'),
            ],
            'context': ctx,
        })
        if view_id:
            action['view_id'] = view_id
        return action

    @api.model
    def open_journal_items(self, options, params):
        """Enterprise GL Journal Items button — partner view + cumulated balance, no group-by."""
        account_id = params.get('account_id')
        if not account_id:
            raise UserError(_("Missing account for Journal Items."))
        return self._journal_items_action(options, {
            'account_id': account_id,
            'group_by_account': False,
            'view_ref': 'account_fs_report.view_move_line_account',
        })
