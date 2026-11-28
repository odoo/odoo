import datetime
import json
import re
from ast import literal_eval
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.addons.web.controllers.utils import clean_action
from odoo.tools.misc import format_amount

_MONTHS_PER_PERIOD = {
    'month': 1,
    'quarter': 3,
    'year': 12,
}

CLOSING_PREFIXES = ('asset', 'liability')
PL_TYPES = ('income', 'income_other', 'expense', 'expense_other',
            'expense_depreciation', 'expense_direct_cost')
EARNINGS_TYPES = PL_TYPES + ('equity_retained', 'equity_unaffected')
EPS = 0.005

# Mirror account.report.expression engine labels (Enterprise debug popover).
ENGINE_DOMAIN = 'Odoo Domain'
ENGINE_AGGREGATION = 'Aggregate Other Formulas'


class FsReportEngine(models.AbstractModel):
    _name = 'fs.report.engine'
    _description = 'Financial Statement Engine'

    @api.model
    def _report_company(self, options):
        return self.env['res.company'].browse(options['company_ids'][0])

    @api.model
    def _base_domain(self, options):
        domain = [('company_id', 'in', options['company_ids'])]
        if options.get('target_move', 'posted') == 'posted':
            domain.append(('parent_state', '=', 'posted'))
        else:
            domain.append(('parent_state', '!=', 'cancel'))
        if options.get('journal_ids'):
            domain.append(('journal_id', 'in', options['journal_ids']))
        return domain

    @api.model
    def _rate(self, company, report_company, date, cache):
        key = (company.id, date)
        if key not in cache:
            cache[key] = company.currency_id._get_conversion_rate(
                company.currency_id, report_company.currency_id, report_company, date)
        return cache[key]

    @api.model
    def _average_rate(self, company, report_co, date_from, date_to, cache):
        """Day-weighted mean, from date_from to date_to inclusive, of the daily
        conversion factor company currency -> report currency."""
        rate_dates = self.env['res.currency.rate'].sudo().search([
            ('currency_id', 'in', [company.currency_id.id, report_co.currency_id.id]),
            ('company_id', 'in', [False, report_co.id]),
            ('name', '>', date_from), ('name', '<=', date_to),
        ]).mapped('name')
        points = sorted(set([date_from] + rate_dates))
        total = 0.0
        for i, start in enumerate(points):
            end = points[i + 1] - timedelta(days=1) if i + 1 < len(points) else date_to
            # Odoo 20 _get_rates uses name < date; +1 day makes rate dated
            # `start` apply from `start` inclusive (day-weighted average).
            total += ((end - start).days + 1) * self._rate(
                company, report_co, start + timedelta(days=1), cache)
        return total / ((date_to - date_from).days + 1)

    @api.model
    def _collect(self, options, domain, date_to):
        """Return [(account_id, hist, close)] in the report currency.
        hist  = each line converted at the rate of its own date.
        close = each line converted at the rate of date_to."""
        report_co = self._report_company(options)
        date_to = fields.Date.to_date(date_to)
        cache, out = {}, []
        MoveLine = self.env['account.move.line']
        for company in self.env['res.company'].browse(options['company_ids']):
            dom = domain + [('company_id', '=', company.id)]
            if company.currency_id == report_co.currency_id:
                for acc, bal in MoveLine._read_group(
                        dom, groupby=['account_id'], aggregates=['balance:sum']):
                    out.append((acc.id, bal, bal))
            else:
                close_rate = self._rate(company, report_co, date_to, cache)
                for acc, day, bal in MoveLine._read_group(
                        dom, groupby=['account_id', 'date:day'], aggregates=['balance:sum']):
                    day = fields.Date.to_date(day)
                    out.append((acc.id, bal * self._rate(company, report_co, day, cache),
                                bal * close_rate))
        return out

    @api.model
    def _balances_by_account(self, options, date_to):
        """{account_id: (hist, close)} for all lines dated <= date_to."""
        date_to = fields.Date.to_date(date_to)
        domain = self._base_domain(options) + [('date', '<=', date_to)]
        res = {}
        for acc_id, hist, close in self._collect(options, domain, date_to):
            h, c = res.get(acc_id, (0.0, 0.0))
            res[acc_id] = (h + hist, c + close)
        return res

    @api.model
    def _period_balances_by_account(self, options, date_from, date_to):
        """{account_id: (hist, hist)} for move lines in [date_from, date_to].

        Enterprise P&L domain engine uses strict_range (date_from..date_to) with
        entry-date FX conversion (hist). Closing rate is unused for period reports.
        """
        date_from = fields.Date.to_date(date_from)
        date_to = fields.Date.to_date(date_to)
        domain = self._base_domain(options) + [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        res = {}
        for acc_id, hist, _close in self._collect(options, domain, date_to):
            h, _ = res.get(acc_id, (0.0, 0.0))
            total = h + hist
            res[acc_id] = (total, total)
        return res

    @api.model
    def _earnings(self, options, date_to):
        """(current_year, previous_years), debit-credit, in report currency.
        Current year: each company's balance converted at the AVERAGE rate from the
        fiscal-year start to date_to. Previous years: entry-date rate."""
        date_to = fields.Date.to_date(date_to)
        report_co = self._report_company(options)
        fy_start = report_co.compute_fiscalyear_dates(date_to)['date_from']
        base = self._base_domain(options) + [
            ('account_id.account_type', 'in', EARNINGS_TYPES)]
        MoveLine = self.env['account.move.line']
        cache, cur = {}, 0.0
        for company in self.env['res.company'].browse(options['company_ids']):
            rows = MoveLine._read_group(
                base + [('company_id', '=', company.id),
                        ('date', '>=', fy_start), ('date', '<=', date_to)],
                aggregates=['balance:sum'])
            bal = rows[0][0] or 0.0
            if not bal:
                continue
            if company.currency_id == report_co.currency_id:
                cur += bal
            else:
                cur += bal * self._average_rate(company, report_co, fy_start, date_to, cache)
        prev = sum(h for _a, h, _c in self._collect(
            options, base + [('date', '<', fy_start)], date_to))
        return cur, prev

    @api.model
    def _aggregation_formula_display(self, aggregation):
        """Turn `TA-TL` / `BANK+REC` into Enterprise-style `TA.balance - TL.balance`."""
        terms = []
        for index, (sign, code) in enumerate(re.findall(r'([+-]?)\s*([A-Za-z0-9_]+)', aggregation or '')):
            token = f'{code}.balance'
            if index == 0:
                terms.append(f'-{token}' if sign == '-' else token)
            else:
                terms.append(f'- {token}' if sign == '-' else f'+ {token}')
        return ' '.join(terms)

    @api.model
    def _domain_formula_display(self, account_types):
        types = [item.strip() for item in (account_types or '').split(',') if item.strip()]
        if len(types) == 1:
            return repr([('account_id.account_type', '=', types[0])])
        return repr([('account_id.account_type', 'in', types)])

    @api.model
    def _debug_popup_data(self, line, value, currency):
        """Build Enterprise `debug_popup_data` JSON for the expression info popover."""
        subformula = None
        if line.formula_type == 'aggregation':
            engine = ENGINE_AGGREGATION
            formula = self._aggregation_formula_display(line.aggregation)
        elif line.formula_type == 'none' and line.child_ids:
            engine = ENGINE_AGGREGATION
            formula = ' + '.join(
                f'{child.code}.balance' for child in line.child_ids.sorted('sequence')
            )
        elif line.formula_type == 'account_type':
            engine = ENGINE_DOMAIN
            formula = self._domain_formula_display(line.account_types)
            subformula = '-sum' if line.sign < 0 else 'sum'
        elif line.formula_type == 'current_earnings':
            engine = ENGINE_DOMAIN
            formula = repr([('account_id.account_type', 'in', list(EARNINGS_TYPES))])
            subformula = '-sum' if line.sign < 0 else 'sum'
        elif line.formula_type == 'previous_earnings':
            engine = ENGINE_DOMAIN
            formula = repr([('account_id.account_type', 'in', list(EARNINGS_TYPES))])
            subformula = '-sum' if line.sign < 0 else 'sum'
        else:
            return False

        info = {
            'formula': formula,
            'subformula': subformula,
            'value': format_amount(self.env, value, currency),
        }
        return json.dumps({
            'expressions_detail': [(engine, [('balance', info)])],
        })

    @api.model
    def _horizontal_split_side(self, line):
        """Walk parents for Enterprise horizontal_split_side (set on section roots)."""
        current = line
        while current:
            if current.horizontal_split_side:
                return current.horizontal_split_side
            current = current.parent_id
        return False

    @api.model
    def get_report_data(self, report_id, options):
        self = self.with_context(allowed_company_ids=options['company_ids'])
        report = self.env['fs.report'].browse(report_id)
        if report.report_type == 'cash_flow':
            return self.env['fs.cash.flow'].get_report_data(report, options)
        columns = options['columns']
        n = len(columns)
        Account = self.env['account.account'].sudo()
        is_period = report.report_type == 'period'

        per_col = []
        for col in columns:
            if is_period:
                bal = self._period_balances_by_account(
                    options, col['date_from'], col['date_to'],
                )
                types = {a.id: a.account_type for a in Account.browse(list(bal))}
                per_col.append((bal, types, 0.0, 0.0))
            else:
                bal = self._balances_by_account(options, col['date_to'])
                types = {a.id: a.account_type for a in Account.browse(list(bal))}
                cur, prev = self._earnings(options, col['date_to'])
                per_col.append((bal, types, cur, prev))

        lines = report.line_ids.sorted('sequence')
        by_code = {l.code: l for l in lines}
        values = {}

        def leaf_value(line):
            wanted = {t.strip() for t in (line.account_types or '').split(',') if t.strip()}
            vals = []
            for bal, types, cur, prev in per_col:
                if line.formula_type == 'account_type':
                    total = 0.0
                    for a, (h, c) in bal.items():
                        t = types[a]
                        if t in wanted:
                            # Period (P&L): always entry-date hist. BS: closing for BS accounts.
                            if is_period:
                                total += h
                            else:
                                total += c if t.startswith(CLOSING_PREFIXES) else h
                    vals.append(line.sign * total)
                elif line.formula_type == 'current_earnings':
                    vals.append(line.sign * cur)
                elif line.formula_type == 'previous_earnings':
                    vals.append(line.sign * prev)
                else:
                    vals.append(0.0)
            return vals

        def compute(line):
            if line.code in values:
                return values[line.code]
            if line.formula_type == 'aggregation':
                total = [0.0] * n
                for sgn, code in re.findall(r'([+-]?)\s*([A-Za-z0-9_]+)', line.aggregation or ''):
                    f = -1 if sgn == '-' else 1
                    total = [t + f * x for t, x in zip(total, compute(by_code[code]))]
                res = [line.sign * t for t in total]
            elif line.formula_type == 'none' and line.child_ids:
                total = [0.0] * n
                for ch in line.child_ids.sorted('sequence'):
                    total = [t + x for t, x in zip(total, compute(ch))]
                res = total
            else:
                res = leaf_value(line)
            values[line.code] = res
            return res

        for line in lines:
            compute(line)

        # Avoid IEEE signed zeros (liability sign * 0.0 → -0.0) skewing growth / muted.
        for code, vals in values.items():
            values[code] = [0.0 if abs(v) < EPS else v for v in vals]

        # Enterprise: debug column only with developer mode and a single column group.
        show_debug = (
            self.env.user.has_group('base.group_no_one')
            and n == 1
            and bool(lines)
        )
        currency = self._report_company(options).currency_id
        out = []

        def emit(line, depth):
            vals = values.get(line.code, [0.0] * n)
            if line.hide_if_zero and all(abs(v) < EPS for v in vals):
                return
            # Enterprise hierarchy_level overrides tree depth when set (>= 0).
            level = line.hierarchy_level if line.hierarchy_level >= 0 else depth
            row = {
                'id': line.id, 'code': line.code, 'name': line.name,
                'parent_id': line.parent_id.id or False,
                'level': level,
                'formula_type': line.formula_type,
                'account_types': line.account_types or '',
                'sign': line.sign,
                'unfoldable': line.formula_type == 'account_type' and line.unfold_accounts,
                'columns': vals,
                'hide_if_zero': line.hide_if_zero,
                'horizontal_split_side': self._horizontal_split_side(line),
                # Enterprise paints action lines with .clickable (teal/action color).
                'action_id': line.action_id.id or False,
                # Domain/custom lines are auditable → amount is a link; row hover uses action color.
                'auditable': line.formula_type in (
                    'account_type', 'current_earnings', 'previous_earnings',
                ),
                # Enterprise expression.green_on_positive (False → red on increase).
                'green_on_positive': bool(line.green_on_positive),
            }
            if show_debug:
                debug = self._debug_popup_data(line, vals[0], currency)
                if debug:
                    row['debug_popup_data'] = debug
            out.append(row)
            for ch in line.child_ids.sorted('sequence'):
                emit(ch, depth + 1)

        for top in lines.filtered(lambda l: not l.parent_id).sorted('sequence'):
            emit(top, 0)
        return {
            'lines': out,
            'has_unposted': self._has_unposted_moves(options),
        }

    @api.model
    def _options_date_to(self, options):
        date_to = (options.get('date') or {}).get('date_to')
        if date_to:
            return date_to
        columns = options.get('columns') or []
        if columns:
            return max(col['date_to'] for col in columns)
        return fields.Date.to_string(fields.Date.context_today(self))

    @api.model
    def _has_unposted_moves(self, options):
        """Enterprise account.report._generate_common_warnings draft-in-period."""
        company_ids = options.get('company_ids') or []
        if not company_ids:
            return False
        return bool(self.env['account.move'].search_count([
            ('company_id', 'in', company_ids),
            ('state', '=', 'draft'),
            ('date', '<=', self._options_date_to(options)),
        ], limit=1))

    @api.model
    def open_unposted_moves(self, options):
        """Open draft journal entries that might impact the reporting (Enterprise)."""
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_journal_line')
        action['domain'] = [
            ('state', '=', 'draft'),
            ('date', '<=', self._options_date_to(options)),
            ('company_id', 'in', options.get('company_ids') or []),
        ]
        # Overwrite context to avoid default filtering on 'misc' journals (Enterprise).
        action['context'] = {}
        return action

    @api.model
    def get_account_lines(self, line_id, options):
        self = self.with_context(allowed_company_ids=options['company_ids'])
        # Cash Flow uses string layout ids (opening_balance, …), not fs.report.line.
        if isinstance(line_id, str) or options.get('report_type') == 'cash_flow':
            return self.env['fs.cash.flow'].get_account_lines(line_id, options)
        line = self.env['fs.report.line'].browse(line_id)
        if not line.exists():
            return self.env['fs.cash.flow'].get_account_lines(line_id, options)
        report = line.report_id
        is_period = report.report_type == 'period'
        wanted = {t.strip() for t in (line.account_types or '').split(',') if t.strip()}
        Account = self.env['account.account'].sudo()
        n = len(options['columns'])
        out = {}
        for i, col in enumerate(options['columns']):
            if is_period:
                bal = self._period_balances_by_account(
                    options, col['date_from'], col['date_to'],
                )
            else:
                bal = self._balances_by_account(options, col['date_to'])
            for acc_id, (h, c) in bal.items():
                acc = Account.browse(acc_id)
                if acc.account_type in wanted:
                    if is_period:
                        val = h
                    else:
                        val = c if acc.account_type.startswith(CLOSING_PREFIXES) else h
                    row = out.setdefault(acc_id, {
                        'id': acc_id,
                        'name': acc.display_name,
                        'code': acc.code,
                        'columns': [0.0] * n,
                        # Enterprise: caret_options key → General Ledger menu on account lines.
                        'caret_options': 'account.account',
                    })
                    row['columns'][i] = line.sign * val
        return sorted(out.values(), key=lambda r: r['name'])

    @api.model
    def caret_option_open_general_ledger(self, options, params):
        """Delegate to Community GL report (Enterprise-parity client action)."""
        return self.env['fs.general.ledger'].caret_option_open_general_ledger(options, params)

    @api.model
    def execute_action(self, options, params=None):
        """Enterprise account.report.execute_action — e.g. CYE line → Profit and Loss.

        Opens ``line.action_id``. When the target is another FS client report, build
        options via the same previous_options rules as Enterprise ``get_options``.
        """
        params = params or {}
        action_id = int(params.get('actionId'))
        action = self.env['ir.actions.actions'].sudo().browse(action_id)
        action_type = action.type
        action = self.env[action_type].sudo().browse(action_id)
        action_read = clean_action(action.read()[0], env=action.env)

        if action_type == 'ir.actions.client' and action.tag == 'account_fs_report.main':
            action_read['params'] = {
                'options': self._options_for_linked_report(options, action_read),
                'ignore_session': True,
            }

        if params.get('id'):
            context = action_read.get('context') and literal_eval(str(action_read['context'])) or {}
            model_id = params['id'] if isinstance(params['id'], int) else params['id']
            context.setdefault('active_id', model_id)
            action_read['context'] = context

        return action_read

    @api.model
    def _compute_period_range(self, date_in_period, months_per_period, start_day=1, start_month=1):
        """Enterprise account.report._compute_period_range."""
        date_in_period = fields.Date.to_date(date_in_period)
        aligned_date = date_in_period + relativedelta(days=-(start_day - 1))
        year = aligned_date.year
        month_offset = aligned_date.month - start_month
        period_number = (month_offset // months_per_period) + 1
        if date_in_period < datetime.date(date_in_period.year, start_month, start_day):
            year -= 1
            period_number = ((12 + month_offset) // months_per_period) + 1
        month_delta = period_number * months_per_period
        end_date = datetime.date(year, start_month, 1) + relativedelta(
            months=month_delta, days=start_day - 2,
        )
        start_date = datetime.date(year, start_month, 1) + relativedelta(
            months=month_delta - months_per_period, day=start_day,
        )
        return start_date, end_date

    @api.model
    def _fiscal_period_start_day_month(self, company):
        """Day/month after fiscalyear last day — same as FS client fiscalStart*."""
        last_month = int(company.fiscalyear_last_month or 12)
        last_day = company.fiscalyear_last_day or 31
        default_year = 2024 if last_month == 2 and last_day == 29 else 2025
        fy_start = datetime.date(default_year, last_month, last_day) + relativedelta(days=1)
        return fy_start.day, fy_start.month

    @api.model
    def _linked_report_dates(self, options, target_report):
        """Enterprise ``_init_options_date`` for previous_options → target report.

        Balance Sheet is single-date; P&amp;L is range_mode. Critical cases:
        - ``today`` → range: [FY start, as-of] with period_type ``custom``
          (not full fiscal year end — matches CYE ``from_fiscalyear``).
        - ``month`` / ``quarter`` / ``year`` → that period's [from, to].
        - ``custom`` → keep bounds; fill date_from with FY start when missing.
        """
        date_opts = options.get('date') or {}
        today = fields.Date.context_today(self)
        date_to = fields.Date.to_date(date_opts['date_to']) if date_opts.get('date_to') else today
        date_from = fields.Date.to_date(date_opts['date_from']) if date_opts.get('date_from') else None
        period_type = date_opts.get('period_type') or 'today'
        company = self.env['res.company'].browse(
            (options.get('company_ids') or [self.env.company.id])[0]
        )
        start_day, start_month = self._fiscal_period_start_day_month(company)
        range_mode = target_report.report_type in ('period', 'cash_flow')

        if not range_mode:
            # Target is single-date (e.g. P&amp;L → BS): keep as-of, drop range start.
            if period_type in _MONTHS_PER_PERIOD:
                _start, date_to = self._compute_period_range(
                    date_to, _MONTHS_PER_PERIOD[period_type], start_day, start_month,
                )
            return False, date_to, period_type if period_type != 'custom' else 'custom'

        # Range mode (P&amp;L)
        if period_type == 'today':
            date_from = company.compute_fiscalyear_dates(date_to)['date_from']
            period_type = 'custom'
        elif period_type == 'custom':
            if not date_from:
                date_from = company.compute_fiscalyear_dates(date_to)['date_from']
        elif period_type in _MONTHS_PER_PERIOD:
            date_from, date_to = self._compute_period_range(
                date_to, _MONTHS_PER_PERIOD[period_type], start_day, start_month,
            )
        else:
            if not date_from:
                date_from = company.compute_fiscalyear_dates(date_to)['date_from']
            period_type = 'custom'

        return date_from, date_to, period_type

    @api.model
    def _options_for_linked_report(self, options, action_read):
        """Map current options onto target FS filter state (applyFilterState keys).

        Mirrors Enterprise ``target_report.get_options(previous_options=options)``.
        """
        context = action_read.get('context') or {}
        if isinstance(context, str):
            context = literal_eval(context)
        report_id = context.get('report_id')
        target = self.env['fs.report'].browse(report_id) if report_id else self.env['fs.report']
        date_from, date_to, period_type = self._linked_report_dates(options, target)
        comparison = options.get('comparison') or {}

        return {
            'periodType': period_type,
            'date_from': fields.Date.to_string(date_from) if date_from else False,
            'date_to': fields.Date.to_string(date_to),
            'customDate': fields.Date.to_string(date_to),
            'customDateFrom': fields.Date.to_string(date_from) if date_from else False,
            'targetMove': options.get('target_move', 'posted'),
            'journalIds': options.get('journal_ids') or [],
            'compare': comparison.get('filter') or 'no_comparison',
            'numberPeriod': comparison.get('number_period') or 1,
            'periodOrder': comparison.get('period_order') or 'descending',
            'growthDisplay': options.get('growth_display') or 'percent',
            'roundingUnit': options.get('rounding_unit') or 'decimals',
        }

    @api.model
    def action_audit_cell(self, options, params):
        """Enterprise action_audit_cell: open Journal Items for the clicked figure."""
        self = self.with_context(allowed_company_ids=options['company_ids'])
        column_index = params.get('column_index', len(options['columns']) - 1)
        column = options['columns'][column_index]
        # Pass column dates through options.date so JI search defaults match Enterprise.
        audit_options = {
            **options,
            'date': {
                **(options.get('date') or {}),
                'date_from': column.get('date_from') or False,
                'date_to': column['date_to'],
                'period_type': (options.get('date') or {}).get('period_type') or 'custom',
            },
        }
        Gl = self.env['fs.general.ledger']
        account_id = params.get('account_id')
        line_id = params.get('line_id')

        if account_id:
            return Gl._journal_items_action(audit_options, {
                'account_id': account_id,
                'group_by_account': False,
            })

        if not line_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Audit'),
                    'message': _('Missing line to audit.'),
                    'type': 'warning',
                    'sticky': False,
                },
            }

        line = self.env['fs.report.line'].browse(line_id)
        if line.formula_type == 'account_type':
            types = [t.strip() for t in (line.account_types or '').split(',') if t.strip()]
            return Gl._journal_items_action(audit_options, {
                'group_by_account': True,
                'extra_domain': [('account_id.account_type', 'in', types)],
            })

        if line.formula_type in ('current_earnings', 'previous_earnings'):
            company = self._report_company(options)
            fy_start = company.compute_fiscalyear_dates(fields.Date.to_date(column['date_to']))['date_from']
            extra = [('account_id.account_type', 'in', list(EARNINGS_TYPES))]
            if line.formula_type == 'current_earnings':
                audit_options = {
                    **audit_options,
                    'date': {
                        **audit_options['date'],
                        'date_from': fields.Date.to_string(fy_start),
                        'date_to': column['date_to'],
                    },
                }
            else:
                # Before FY start — no date_from search; keep bound in domain.
                audit_options = {
                    **audit_options,
                    'date': {
                        **audit_options['date'],
                        'date_from': False,
                        'date_to': fields.Date.to_string(fy_start - timedelta(days=1)),
                    },
                }
            return Gl._journal_items_action(audit_options, {
                'group_by_account': True,
                'extra_domain': extra,
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Audit'),
                'message': _('This line has no journal items to audit.'),
                'type': 'warning',
                'sticky': False,
            },
        }
