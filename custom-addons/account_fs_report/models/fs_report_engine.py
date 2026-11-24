import json
import re
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.tools.misc import format_amount

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
        columns = options['columns']
        n = len(columns)
        Account = self.env['account.account'].sudo()

        per_col = []
        for col in columns:
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

        def emit(line, level):
            vals = values.get(line.code, [0.0] * n)
            if line.hide_if_zero and all(abs(v) < EPS for v in vals):
                return
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
                emit(ch, level + 1)

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
        line = self.env['fs.report.line'].browse(line_id)
        wanted = {t.strip() for t in (line.account_types or '').split(',') if t.strip()}
        Account = self.env['account.account'].sudo()
        n = len(options['columns'])
        out = {}
        for i, col in enumerate(options['columns']):
            bal = self._balances_by_account(options, col['date_to'])
            for acc_id, (h, c) in bal.items():
                acc = Account.browse(acc_id)
                if acc.account_type in wanted:
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
    def action_audit_cell(self, options, params):
        """Enterprise action_audit_cell: open Journal Items for the clicked figure."""
        self = self.with_context(allowed_company_ids=options['company_ids'])
        column_index = params.get('column_index', len(options['columns']) - 1)
        date_to = options['columns'][column_index]['date_to']
        domain = self._base_domain(options) + [
            ('display_type', 'not in', ('line_section', 'line_subsection', 'line_note')),
        ]

        account_id = params.get('account_id')
        line_id = params.get('line_id')
        if account_id:
            domain += [
                ('account_id', '=', account_id),
                ('date', '<=', date_to),
            ]
        elif line_id:
            line = self.env['fs.report.line'].browse(line_id)
            if line.formula_type == 'account_type':
                types = [t.strip() for t in (line.account_types or '').split(',') if t.strip()]
                domain += [
                    ('account_id.account_type', 'in', types),
                    ('date', '<=', date_to),
                ]
            elif line.formula_type in ('current_earnings', 'previous_earnings'):
                company = self._report_company(options)
                fy_start = company.compute_fiscalyear_dates(fields.Date.to_date(date_to))['date_from']
                domain.append(('account_id.account_type', 'in', list(EARNINGS_TYPES)))
                if line.formula_type == 'current_earnings':
                    domain += [
                        ('date', '>=', fields.Date.to_string(fy_start)),
                        ('date', '<=', date_to),
                    ]
                else:
                    domain.append(('date', '<', fields.Date.to_string(fy_start)))
            else:
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
        else:
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

        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all')
        action.update({
            'name': _('Journal Items'),
            'domain': domain,
            # Enterprise audit opens list/pivot/graph/kanban with Balance Sheet breadcrumb.
            'view_mode': 'list,pivot,graph,kanban',
            'views': [
                (False, 'list'),
                (False, 'pivot'),
                (False, 'graph'),
                (False, 'kanban'),
            ],
            'context': {
                **dict(self.env.context),
                'create': 0,
                'search_default_posted': 1 if options.get('target_move', 'posted') == 'posted' else 0,
                'search_default_group_by_account': 0 if account_id else 1,
            },
        })
        return action
