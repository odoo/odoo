# Part of Odoo. See LICENSE file for full copyright and licensing details.
import csv
import re
from functools import lru_cache

from odoo import api, fields, models
from odoo.tools import file_open

# An account prefix or range bound: digits and 'x' wildcards, in any
# position, e.g. '1088', '101x', '80xx', '1x10'.
_PREFIX_RE = re.compile(r'^[0-9x]+$', re.IGNORECASE)


def _parse_prefix(value):
    """Validate an account prefix or range bound (wildcards allowed anywhere).

    :param str value: e.g. '1088', '1x10', '80xx'.
    :return: the cleaned value, or None if it isn't a valid prefix.
    :rtype: str|None
    """
    value = value.strip().lower()
    return value if _PREFIX_RE.match(value) else None


def _parse_item(item):
    """Parse a single comma-separated item into a token tuple.

    An item is either a plain account prefix ('1102', '80xx', '1x10')
    or an inclusive range expressed with '..' ('101x..109x',
    '1x10..1x20'). Wildcards ('x') are allowed anywhere in a prefix or
    a range bound; within a range, each 'x' is replaced with '0' on the
    low bound and '9' on the high bound, so the range becomes a plain
    numeric interval (e.g. '1x10..1x20' matches every account from 1010
    to 1920, not just the 1_10/1_20 "family").

    :param str item: a single item, already stripped of surrounding
        commas/dashes.
    :return: ('prefix', value) or ('range', low, high), or None if the
        item is malformed.
    :rtype: tuple|None
    """
    item = item.strip()
    if not item:
        return None
    if '..' in item:
        low, _, high = item.partition('..')
        low, high = _parse_prefix(low), _parse_prefix(high)
        if low is None or high is None:
            return None
        return ('range', low, high)
    value = _parse_prefix(item)
    return ('prefix', value) if value is not None else None


def _parse_item_list(text):
    """Parse a comma-separated list of items (used for includes and excludes).

    :param str text: e.g. '101x..109x,1102'.
    :return: list of parsed tokens. Malformed items are silently dropped.
    :rtype: list
    """
    if not text:
        return []
    tokens = (_parse_item(part) for part in text.split(','))
    return [token for token in tokens if token is not None]


def _strip_direction(expression):
    """Strip optional C/D direction prefix from an expression string.

    :param str expression: raw expression possibly starting with C or D.
    :return: tuple of (direction, remaining_expression).
    :rtype: tuple[str|None, str]
    """
    if expression and expression[0].upper() in ('C', 'D'):
        return expression[0].upper(), expression[1:]
    return None, expression


def _parse_expression(expression):
    """Parse a BAS account_expression into a structured dict.

    Grammar::

        [C|D] <includes>[-<excludes>]
        includes := item (',' item)*
        excludes := item (',' item)*
        item      := prefix | prefix '..' prefix
        prefix    := digits and 'x' wildcards, in any position

    - 'x' is a wildcard digit and may appear anywhere in a prefix or a
      range bound, e.g. '10xx' or '1x10'.
    - '..' defines an inclusive range between two prefixes/wildcards.
      Each 'x' in a range bound is replaced with '0' on the low bound
      and '9' on the high bound, so the range becomes a plain numeric
      interval, e.g. '101x..109x' covers 1010-1099.
    - ',' adds another independent item to the current list (include or
      exclude).
    - '-' switches from the include list to the exclude list. Only the
      *first* '-' in the expression matters; everything after it is
      excluded from everything matched by the include list, regardless
      of further commas.

    Example::

        '101x..109x,1102-1015..1019,1021'
        -> includes: 1010-1099 and 1102
           excludes: 1015-1019 and 1021

    :param str expression: the account expression string.
    :return: dict with keys 'direction' (str|None), 'includes' (list),
             'excludes' (list), or None if unparseable.
    :rtype: dict|None
    """
    expression = expression.strip()
    if not expression:
        return None

    direction, expression = _strip_direction(expression)
    if not expression:
        return None

    include_text, _, exclude_text = expression.partition('-')
    includes = _parse_item_list(include_text)
    if not includes:
        return None
    excludes = _parse_item_list(exclude_text)

    return {'direction': direction, 'includes': includes, 'excludes': excludes}


@lru_cache(maxsize=2048)
def _parse_expression_cached(expression):
    """Cached, immutable variant of _parse_expression used for matching."""
    parsed = _parse_expression(expression)
    if parsed is None:
        return None
    return parsed['direction'], tuple(parsed['includes']), tuple(parsed['excludes'])


def _account_matches_token(account, token):
    """Check whether an account code matches a single include/exclude token.

    :param str account: the account code, e.g. '1510'.
    :param tuple token: ('prefix', '15xx') or ('range', '10', '19').
    :return: True if the account matches the token.
    :rtype: bool
    """
    kind = token[0]
    if kind == 'prefix':
        pattern = token[1].replace('x', r'\d')
        return bool(re.match(r'^' + pattern, account))
    # kind == 'range'
    low_raw, high_raw = token[1], token[2]
    low_norm = low_raw.replace('x', '0')
    high_norm = high_raw.replace('x', '9')
    length = max(len(low_norm), len(high_norm))
    low_clean = low_norm.ljust(length, '0')
    high_clean = high_norm.ljust(length, '9')
    account_prefix = account[:length].ljust(length, '0')
    return low_clean <= account_prefix <= high_clean


def _matches(account, direction, expression):
    """Return True if (account, direction) matches the given account_expression.

    :param str account: account code, e.g. '1510'.
    :param str direction: 'D', 'C', or '' for unknown/both.
    :param str expression: BAS account expression, e.g. 'C80..82,8110'.
    :return: True if the account and direction match the expression.
    :rtype: bool
    """
    parsed = _parse_expression_cached(expression)
    if parsed is None:
        return False

    expr_dir, includes, excludes = parsed
    if expr_dir and direction and expr_dir != direction.upper():
        return False

    if not any(_account_matches_token(account, t) for t in includes):
        return False

    return not any(_account_matches_token(account, t) for t in excludes)


def _resolve_sru_code(account_code, direction, mappings):
    """Find the SRU code for a single (account, direction) pair.

    Iterates over the cached mappings recordset and returns the first match.

    :param str account_code: BAS account code, e.g. '1510'.
    :param str direction: 'D' or 'C'.
    :param recordset mappings: l10n_se.sru.mapping records for the company.
    :return: the matched SRU code string, or None if no match found.
    :rtype: str|None
    """
    for mapping in mappings:
        if _matches(account_code, direction, mapping.account_expression):
            return mapping.sru_code
    return None


# SRU form per chart template. INK3 (non-profit associations, foundations, ...)
# cannot be derived from the chart and must be requested explicitly.
SRU_TYPES = [
    ('ink2', 'INK2 - Limited companies, economic associations'),
    ('ink3', 'INK3 - Non-profit associations, foundations'),
    ('ink4', 'INK4 - Trading partnerships'),
    ('ne', 'NE - Sole traders'),
]

SRU_TYPE_BY_TEMPLATE = {
    'se_K1': 'ne',
    'se_K2': 'ink2',
    'se_K3': 'ink2',
    'se_K2_HB': 'ink4',
    'se_K2_NPO': 'ink3',
}


class L10nSeSruMapping(models.Model):
    """Mapping of BAS account expressions to SRU codes per company and SRU type."""

    _name = 'l10n_se.sru.mapping'
    _description = 'Mapping of Account Expressions to SRU Codes'
    _rec_name = 'account_expression'
    _order = 'sequence, id'
    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    sequence = fields.Integer(
        default=10,
        help=(
            'Determines match priority when several rows could match the '
            'same account: the first matching row in sequence order wins. '
            'Rows loaded from the built-in template keep the order of '
            'the source CSV file.'
        ),
    )
    account_expression = fields.Char(
        required=True,
        index=True,
        help=(
            'BAS account expression. Optional C (credit) or D (debit) '
            'prefix for direction, no prefix means both. "x" is a '
            'wildcard digit and may appear anywhere in a prefix or '
            'range bound (e.g. "10xx", "1x10"). Use ".." for an '
            'inclusive range (e.g. "1010..1019"; a wildcard in a '
            'range bound is replaced by 0 on the low end and 9 on '
            'the high end). Use "," to add further prefixes/ranges '
            'to the include or exclude list, and "-" once to start '
            'the exclude list (everything after it, across all '
            'commas, is excluded). '
            'Examples: "10..19,1088", "C80..82,8110", '
            '"D49-4910..4929,496,498"'
        ),
    )
    sru_code = fields.Char(required=True, index=True)
    sru_type = fields.Selection(
        SRU_TYPES,
        string='SRU Type',
        required=True,
        default='ink2',
    )

    _unique_account_expression_sru = models.Constraint(
        'unique(company_id, sru_type, account_expression, sru_code)',
        'Each account expression can only be mapped once per SRU code and company.',
    )

    @api.model
    def _get_sru_type(self, company, sru_type=None):
        """Return the SRU form to use for the company.

        Priority: the explicit ``sru_type`` argument, then the form chosen on the
        company (Settings > Accounting), then the form derived from the chart.

        :param res.company company: the company.
        :param str sru_type: explicit SRU type; overrides the company setting.
        :return: 'ink2', 'ink3', 'ink4', 'ne' or False if it cannot be determined.
        :rtype: str|bool
        """
        return (
            sru_type
            or company.l10n_se_sru_type
            or SRU_TYPE_BY_TEMPLATE.get(company.chart_template, False)
        )

    def _get_mappings(self, company, sru_type):
        return self.search([
            ('company_id', '=', company.id),
            ('sru_type', '=', sru_type),
        ])

    @api.model
    def get_all_sru_codes(self, company=None, sru_type=None):
        """Return a list of all unique SRU codes for the given company.

        :param res.company company: company to use, defaults to current company.
        :param str sru_type: explicit SRU type, defaults to the one derived from the chart.
        :return: unique SRU codes, or empty list if no SRU type can be determined.
        :rtype: list
        """
        company = company or self.env.company
        sru_type = self._get_sru_type(company, sru_type)
        if not sru_type:
            return []
        return list(set(self._get_mappings(company, sru_type).mapped('sru_code')))

    @api.model
    def load_template_from_file(self, sru_type=None):
        """Load SRU mappings from the built-in CSV template.

        Replaces all existing mappings for the current company and SRU type
        with the module's bundled template data. Each row's ``sequence`` is
        set from its position in the CSV file (10, 20, 30, ...), so match
        priority stays visible and editable in the UI.

        CSV format: account_expression,sru_code,sru_type
        Direction is encoded in the account_expression prefix (C or D).

        :param str sru_type: explicit SRU type, defaults to the one derived from the chart.
        :return: True on success, False if no SRU type can be determined.
        :rtype: bool
        """
        company = self.env.company
        sru_type = self._get_sru_type(company, sru_type)
        if not sru_type:
            return False

        records_to_create = []
        with file_open(f'l10n_se/data/template/{sru_type}_sru_template.csv', 'r') as csvfile:
            for index, row in enumerate(csv.DictReader(csvfile)):
                records_to_create.append({
                    'company_id': company.id,
                    'sequence': (index + 1) * 10,
                    'account_expression': row['account_expression'],
                    'sru_code': row['sru_code'],
                    'sru_type': sru_type,
                })

        with self.env.cr.savepoint():
            self._get_mappings(company, sru_type).unlink()
            if records_to_create:
                self.create(records_to_create)
        return True

    @api.model
    def _fetch_account_balances(self, company, date_from, date_to, include_unposted):
        """Return the balance (debit - credit) per account code, as reported in the return.

        Balance sheet accounts (those carrying their balance forward) are reported
        with their closing balance at ``date_to``: everything booked up to that date.
        Profit and loss accounts are reported with the movements of the period.

        :param res.company company: the company to query.
        :param date date_from: start of the income year (inclusive).
        :param date date_to: end of the income year (inclusive).
        :param bool include_unposted: whether to include draft moves.
        :return: dict mapping account code to balance.
        :rtype: dict[str, float]
        """
        states = ['posted', 'draft'] if include_unposted else ['posted']
        groups = self.env['account.move.line']._read_group(
            domain=[
                ('company_id', '=', company.id),
                ('date', '<=', date_to),
                ('parent_state', 'in', states),
                '|',
                ('account_id.include_initial_balance', '=', True),
                ('date', '>=', date_from),
            ],
            groupby=['account_id'],
            aggregates=['balance:sum'],
        )
        return {
            account.with_company(company).code: balance
            for account, balance in groups
            if account
        }

    @api.model
    def get_sru_codes(self, account_balances, company=None, sru_type=None):
        """Return SRU codes for a dict of account balances.

        Direction (D/C) is determined from the sign of the balance:
        positive balance = D (debit), negative balance = C (credit).
        Accounts with zero balance or no mapping are excluded from the result.

        :param dict account_balances: account code to net balance (debit - credit),
            e.g. {'1510': 25000.0, '8990': -150000.0}.
        :param res.company company: company to use, defaults to current company.
        :param str sru_type: explicit SRU type, defaults to the one derived from the chart.
        :return: dict mapping account code to SRU code, e.g. {'1510': '7251'}.
        :rtype: dict[str, str]
        """
        company = company or self.env.company
        sru_type = self._get_sru_type(company, sru_type)
        if not sru_type:
            return {}

        mappings = self._get_mappings(company, sru_type)
        result = {}
        for account_code, balance in account_balances.items():
            if not balance:
                continue
            direction = 'D' if balance > 0 else 'C'
            sru_code = _resolve_sru_code(account_code, direction, mappings)
            if sru_code:
                result[account_code] = sru_code
        return result

    @api.model
    def get_sru_codes_for_accounts(self, date_from, date_to, company=None, include_unposted=False, sru_type=None):
        """Return SRU codes for all accounts with movements in the given period.

        :param date date_from: start of the period (inclusive).
        :param date date_to: end of the period (inclusive).
        :param res.company company: company to use, defaults to current company.
        :param bool include_unposted: if True, include draft move lines as well.
        :param str sru_type: explicit SRU type, defaults to the one derived from the chart.
        :return: dict mapping account code to SRU code, e.g. {'1510': '7251'}.
        :rtype: dict[str, str]
        """
        company = company or self.env.company
        sru_type = self._get_sru_type(company, sru_type)
        if not sru_type:
            return {}
        balances = self._fetch_account_balances(company, date_from, date_to, include_unposted)
        return self.get_sru_codes(balances, company, sru_type)
