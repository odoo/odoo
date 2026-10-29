# Copyright 2014 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
import re
from collections import defaultdict

from odoo import _, fields
from odoo.exceptions import UserError
from odoo.models import expression
from odoo.tools.float_utils import float_is_zero
from odoo.tools.safe_eval import datetime, dateutil, safe_eval, time

from .accounting_none import AccountingNone
from .simple_array import SimpleArray

_logger = logging.getLogger(__name__)

_DOMAIN_START_RE = re.compile(r"\(|(['\"])[!&|]\1")


def _is_domain(s):
    """Test if a string looks like an Odoo domain"""
    return _DOMAIN_START_RE.match(s)


class AccountingExpressionProcessor:
    """Processor for accounting expressions.

    Expressions of the form <field><mode>[accounts][optional move line domain]
    are supported, where:
        * field is bal, crd, deb, pbal (positive balances only),
          nbal (negative balance only)
        * mode is i (initial balance), e (ending balance),
          p (moves over period)
        * there is also a special u mode (unallocated P&L) which computes
          the sum from the beginning until the beginning of the fiscal year
          of the period; it is only meaningful for P&L accounts
        * accounts is a list of accounts, possibly containing % wildcards,
          or a domain expression on account.account
        * an optional domain on move lines allowing filters on eg analytic
          accounts or journal

    Examples:
        * bal[70]: variation of the balance of moves on account 70
          over the period (it is the same as balp[70]);
        * bali[70,60]: balance of accounts 70 and 60 at the start of period;
        * bale[1%]: balance of accounts starting with 1 at end of period.

    How to use:
        * repeatedly invoke parse_expr() for each expression containing
          accounting variables as described above; this lets the processor
          group domains and modes and accounts;
        * when all expressions have been parsed, invoke done_parsing()
          to notify the processor that it can prepare to query (mainly
          search all accounts - children, consolidation - that will need to
          be queried;
        * for each period, call do_queries(), then call replace_expr() for each
          expression to replace accounting variables with their resulting value
          for the given period.

    How it works:
        * by accumulating the expressions before hand, it ensures to do the
          strict minimum number of queries to the database (for each period,
          one query per domain and mode);
        * it queries using the orm read_group which reduces to a query with
          sum on debit and credit and group by on account_id and company_id,
          (note: it seems the orm then does one query per account to fetch
          the account name...);
        * additionally, one query per view/consolidation account is done to
          discover the children accounts.
    """

    MODE_VARIATION = "p"
    MODE_INITIAL = "i"
    MODE_END = "e"
    MODE_UNALLOCATED = "u"

    _ACC_RE = re.compile(
        r"(?P<field>\bbal|\bpbal|\bnbal|\bcrd|\bdeb)"
        r"(?P<mode>[piseu])?"
        r"\s*"
        r"(?P<account_sel>_[a-zA-Z0-9]+|\[.*?\])"
        r"\s*"
        r"(?P<ml_domain>\[.*?\])?"
    )

    def __init__(self, companies, currency=None, account_model="account.account"):
        self.env = companies.env
        self.companies = companies
        if not currency:
            self.currency = companies.mapped("currency_id")
            if len(self.currency) > 1:
                raise UserError(
                    _(
                        "If currency_id is not provided, "
                        "all companies must have the same currency."
                    )
                )
        else:
            self.currency = currency
        self.dp = self.currency.decimal_places
        # before done_parsing: {(ml_domain, mode): set(acc_domain)}
        # after done_parsing: {(ml_domain, mode): list(account_ids)}
        self._map_account_ids = defaultdict(set)
        # {account_domain: set(account_ids)}
        self._account_ids_by_acc_domain = defaultdict(set)
        # smart ending balance (returns AccountingNone if there
        # are no moves in period and 0 initial balance), implies
        # a first query to get the initial balance and another
        # to get the variation, so it's a bit slower
        self.smart_end = True
        # Account model
        self._account_model = self.env[account_model].with_context(active_test=False)

    def _account_codes_to_domain(self, account_codes):
        """Convert a comma separated list of account codes
        (possibly with wildcards) to a domain on account.account.
        """
        elems = []
        for account_code in account_codes.split(","):
            account_code = account_code.strip()
            if "%" in account_code:
                elems.append([("code", "=like", account_code)])
            else:
                elems.append([("code", "=", account_code)])
        return tuple(expression.OR(elems))

    def _parse_match_object(self, mo):
        """Split a match object corresponding to an accounting variable

        Returns field, mode, account domain, move line domain.
        """
        domain_eval_context = {
            "ref": self.env.ref,
            "user": self.env.user,
            "time": time,
            "datetime": datetime,
            "dateutil": dateutil,
        }
        field, mode, account_sel, ml_domain = mo.groups()
        # handle some legacy modes
        if not mode:
            mode = self.MODE_VARIATION
        elif mode == "s":
            mode = self.MODE_END
        # convert account selector to account domain
        if account_sel.startswith("_"):
            # legacy bal_NNN%
            acc_domain = self._account_codes_to_domain(account_sel[1:])
        else:
            assert account_sel[0] == "[" and account_sel[-1] == "]"
            inner_account_sel = account_sel[1:-1].strip()
            if not inner_account_sel:
                # empty selector: select all accounts
                acc_domain = tuple()
            elif _is_domain(inner_account_sel):
                # account selector is a domain
                acc_domain = tuple(safe_eval(account_sel, domain_eval_context))
            else:
                # account selector is a list of account codes
                acc_domain = self._account_codes_to_domain(inner_account_sel)
        # move line domain
        if ml_domain:
            assert ml_domain[0] == "[" and ml_domain[-1] == "]"
            ml_domain = tuple(safe_eval(ml_domain, domain_eval_context))
        else:
            ml_domain = tuple()
        return field, mode, acc_domain, ml_domain

    def parse_expr(self, expr):
        """Parse an expression, extracting accounting variables.

        Move line domains and account selectors are extracted and
        stored in the map so when all expressions have been parsed,
        we know which account domains to query for each move line domain
        and mode.
        """
        for mo in self._ACC_RE.finditer(expr):
            _, mode, acc_domain, ml_domain = self._parse_match_object(mo)
            if mode == self.MODE_END and self.smart_end:
                modes = (self.MODE_INITIAL, self.MODE_VARIATION, self.MODE_END)
            else:
                modes = (mode,)
            for mode in modes:
                key = (ml_domain, mode)
                self._map_account_ids[key].add(acc_domain)

    def done_parsing(self):
        """Replace account domains by account ids in map"""
        for key, acc_domains in self._map_account_ids.items():
            all_account_ids = set()
            for acc_domain in acc_domains:
                acc_domain_with_company = expression.AND(
                    [acc_domain, [("company_id", "in", self.companies.ids)]]
                )
                account_ids = self._account_model.search(acc_domain_with_company).ids
                self._account_ids_by_acc_domain[acc_domain].update(account_ids)
                all_account_ids.update(account_ids)
            self._map_account_ids[key] = list(all_account_ids)

    @classmethod
    def has_account_var(cls, expr):
        """Test if an string contains an accounting variable."""
        return bool(cls._ACC_RE.search(expr))

    def get_account_ids_for_expr(self, expr):
        """Get a set of account ids that are involved in an expression.

        Prerequisite: done_parsing() must have been invoked.
        """
        account_ids = set()
        for mo in self._ACC_RE.finditer(expr):
            field, mode, acc_domain, ml_domain = self._parse_match_object(mo)
            account_ids.update(self._account_ids_by_acc_domain[acc_domain])
        return account_ids

    def get_aml_domain_for_expr(self, expr, date_from, date_to, account_id=None):
        """Get a domain on account.move.line for an expression.

        Prerequisite: done_parsing() must have been invoked.

        Returns a domain that can be used to search on account.move.line.
        """
        aml_domains = []
        date_domain_by_mode = {}
        for mo in self._ACC_RE.finditer(expr):
            field, mode, acc_domain, ml_domain = self._parse_match_object(mo)
            aml_domain = list(ml_domain)
            account_ids = set()
            account_ids.update(self._account_ids_by_acc_domain[acc_domain])
            if not account_id:
                aml_domain.append(("account_id", "in", tuple(account_ids)))
            else:
                # filter on account_id
                if account_id in account_ids:
                    aml_domain.append(("account_id", "=", account_id))
                else:
                    continue
            if field == "crd":
                aml_domain.append(("credit", "<>", 0.0))
            elif field == "deb":
                aml_domain.append(("debit", "<>", 0.0))
            aml_domains.append(expression.normalize_domain(aml_domain))
            if mode not in date_domain_by_mode:
                date_domain_by_mode[mode] = self.get_aml_domain_for_dates(
                    date_from, date_to, mode
                )
        assert aml_domains
        # TODO we could do this for more precision:
        #      AND(OR(aml_domains[mode]), date_domain[mode]) for each mode
        return expression.OR(aml_domains) + expression.OR(date_domain_by_mode.values())

    def get_aml_domain_for_dates(self, date_from, date_to, mode):
        if mode == self.MODE_VARIATION:
            domain = [("date", ">=", date_from), ("date", "<=", date_to)]
        elif mode in (self.MODE_INITIAL, self.MODE_END):
            # for income and expense account, sum from the beginning
            # of the current fiscal year only, for balance sheet accounts
            # sum from the beginning of time
            date_from_date = fields.Date.from_string(date_from)
            # TODO this takes the fy from the first company
            # make that user controllable (nice to have)?
            fy_date_from = self.companies[0].compute_fiscalyear_dates(date_from_date)[
                "date_from"
            ]
            domain = [
                "|",
                ("date", ">=", fields.Date.to_string(fy_date_from)),
                ("account_id.include_initial_balance", "=", True),
            ]
            if mode == self.MODE_INITIAL:
                domain.append(("date", "<", date_from))
            elif mode == self.MODE_END:
                domain.append(("date", "<=", date_to))
        elif mode == self.MODE_UNALLOCATED:
            date_from_date = fields.Date.from_string(date_from)
            # TODO this takes the fy from the first company
            # make that user controllable (nice to have)?
            fy_date_from = self.companies[0].compute_fiscalyear_dates(date_from_date)[
                "date_from"
            ]
            domain = [
                ("date", "<", fields.Date.to_string(fy_date_from)),
                ("account_id.include_initial_balance", "=", False),
            ]
        return expression.normalize_domain(domain)

    def _get_company_rates(self, date):
        # get exchange rates for each company with its rouding
        company_rates = {}
        target_rate = self.currency.with_context(date=date).rate
        for company in self.companies:
            if company.currency_id != self.currency:
                rate = target_rate / company.currency_id.with_context(date=date).rate
            else:
                rate = 1.0
            company_rates[company.id] = (rate, company.currency_id.decimal_places)
        return company_rates

    def do_queries(
        self,
        date_from,
        date_to,
        additional_move_line_filter=None,
        aml_model=None,
    ):
        """Query sums of debit and credit for all accounts and domains
        used in expressions.

        This method must be executed after done_parsing().
        """
        if not aml_model:
            aml_model = self.env["account.move.line"]
        else:
            aml_model = self.env[aml_model]
        aml_model = aml_model.with_context(active_test=False)
        company_rates = self._get_company_rates(date_to)
        # {(domain, mode): {account_id: (debit, credit)}}
        self._data = defaultdict(
            lambda: defaultdict(
                lambda: SimpleArray((AccountingNone, AccountingNone)),
            )
        )
        domain_by_mode = {}
        ends = []
        for key in self._map_account_ids:
            domain, mode = key
            if mode == self.MODE_END and self.smart_end:
                # postpone computation of ending balance
                ends.append((domain, mode))
                continue
            if mode not in domain_by_mode:
                domain_by_mode[mode] = self.get_aml_domain_for_dates(
                    date_from, date_to, mode
                )
            domain = list(domain) + domain_by_mode[mode]
            domain.append(("account_id", "in", self._map_account_ids[key]))
            if additional_move_line_filter:
                domain.extend(additional_move_line_filter)
            # fetch sum of debit/credit, grouped by account_id
            _logger.debug("read_group domain: %s", domain)
            try:
                accs = aml_model.read_group(
                    domain,
                    ["debit", "credit", "account_id", "company_id"],
                    ["account_id", "company_id"],
                    lazy=False,
                )
            except ValueError as e:
                raise UserError(
                    _(
                        'Error while querying move line source "%(model_name)s". '
                        "This is likely due to a filter or expression referencing "
                        "a field that does not exist in the model.\n\n"
                        "The technical error message is: %(exception)s. "
                    )
                    % dict(
                        model_name=aml_model._description,
                        exception=e,
                    )
                ) from e
            for acc in accs:
                rate, dp = company_rates[acc["company_id"][0]]
                debit = acc["debit"] or 0.0
                credit = acc["credit"] or 0.0
                if mode in (self.MODE_INITIAL, self.MODE_UNALLOCATED) and float_is_zero(
                    debit - credit, precision_digits=self.dp
                ):
                    # in initial mode, ignore accounts with 0 balance
                    continue
                # due to branches, it's possible to have multiple acc
                # with the same account_id
                self._data[key][acc["account_id"][0]] += (debit * rate, credit * rate)
        # compute ending balances by summing initial and variation
        for key in ends:
            domain, mode = key
            initial_data = self._data[(domain, self.MODE_INITIAL)]
            variation_data = self._data[(domain, self.MODE_VARIATION)]
            account_ids = set(initial_data.keys()) | set(variation_data.keys())
            for account_id in account_ids:
                di, ci = initial_data.get(account_id, (AccountingNone, AccountingNone))
                dv, cv = variation_data.get(
                    account_id, (AccountingNone, AccountingNone)
                )
                self._data[key][account_id] = (di + dv, ci + cv)

    def replace_expr(self, expr):
        """Replace accounting variables in an expression by their amount.

        Returns a new expression string.

        This method must be executed after do_queries().
        """

        def f(mo):
            field, mode, acc_domain, ml_domain = self._parse_match_object(mo)
            key = (ml_domain, mode)
            account_ids_data = self._data[key]
            v = AccountingNone
            account_ids = self._account_ids_by_acc_domain[acc_domain]
            for account_id in account_ids:
                debit, credit = account_ids_data.get(
                    account_id, (AccountingNone, AccountingNone)
                )
                if field == "bal":
                    v += debit - credit
                elif field == "pbal" and debit >= credit:
                    v += debit - credit
                elif field == "nbal" and debit < credit:
                    v += debit - credit
                elif field == "deb":
                    v += debit
                elif field == "crd":
                    v += credit
            # in initial balance mode, assume 0 is None
            # as it does not make sense to distinguish 0 from "no data"
            if (
                v is not AccountingNone
                and mode in (self.MODE_INITIAL, self.MODE_UNALLOCATED)
                and float_is_zero(v, precision_digits=self.dp)
            ):
                v = AccountingNone
            return "(" + repr(v) + ")"

        return self._ACC_RE.sub(f, expr)

    def replace_exprs_by_account_id(self, exprs):
        """Replace accounting variables in a list of expression
        by their amount, iterating by accounts involved in the expression.

        yields account_id, replaced_expr

        This method must be executed after do_queries().
        """

        def f(mo):
            field, mode, acc_domain, ml_domain = self._parse_match_object(mo)
            key = (ml_domain, mode)
            # first check if account_id is involved in
            # the current expression part
            if account_id not in self._account_ids_by_acc_domain[acc_domain]:
                return "(AccountingNone)"
            # here we know account_id is involved in acc_domain
            account_ids_data = self._data[key]
            debit, credit = account_ids_data.get(
                account_id, (AccountingNone, AccountingNone)
            )
            if field == "bal":
                v = debit - credit
            elif field == "pbal":
                if debit >= credit:
                    v = debit - credit
                else:
                    v = AccountingNone
            elif field == "nbal":
                if debit < credit:
                    v = debit - credit
                else:
                    v = AccountingNone
            elif field == "deb":
                v = debit
            elif field == "crd":
                v = credit
            # in initial balance mode, assume 0 is None
            # as it does not make sense to distinguish 0 from "no data"
            if (
                v is not AccountingNone
                and mode in (self.MODE_INITIAL, self.MODE_UNALLOCATED)
                and float_is_zero(v, precision_digits=self.dp)
            ):
                v = AccountingNone
            return "(" + repr(v) + ")"

        account_ids = set()
        for expr in exprs:
            for mo in self._ACC_RE.finditer(expr):
                field, mode, acc_domain, ml_domain = self._parse_match_object(mo)
                key = (ml_domain, mode)
                account_ids_data = self._data[key]
                for account_id in self._account_ids_by_acc_domain[acc_domain]:
                    if account_id in account_ids_data:
                        account_ids.add(account_id)

        for account_id in account_ids:
            yield account_id, [self._ACC_RE.sub(f, expr) for expr in exprs]

    @classmethod
    def _get_balances(cls, mode, companies, date_from, date_to):
        expr = f"deb{mode}[], crd{mode}[]"
        aep = AccountingExpressionProcessor(companies)
        # disable smart_end to have the data at once, instead
        # of initial + variation
        aep.smart_end = False
        aep.parse_expr(expr)
        aep.done_parsing()
        aep.do_queries(date_from, date_to)
        return aep._data[((), mode)]

    @classmethod
    def get_balances_initial(cls, companies, date):
        """A convenience method to obtain the initial balances of all accounts
        at a given date.

        It is the same as get_balances_end(date-1).

        :param companies:
        :param date:

        Returns a dictionary: {account_id, (debit, credit)}
        """
        return cls._get_balances(cls.MODE_INITIAL, companies, date, date)

    @classmethod
    def get_balances_end(cls, companies, date):
        """A convenience method to obtain the ending balances of all accounts
        at a given date.

        It is the same as get_balances_initial(date+1).

        :param companies:
        :param date:

        Returns a dictionary: {account_id, (debit, credit)}
        """
        return cls._get_balances(cls.MODE_END, companies, date, date)

    @classmethod
    def get_balances_variation(cls, companies, date_from, date_to):
        """A convenience method to obtain the variation of the
        balances of all accounts over a period.

        :param companies:
        :param date:

        Returns a dictionary: {account_id, (debit, credit)}
        """
        return cls._get_balances(cls.MODE_VARIATION, companies, date_from, date_to)

    @classmethod
    def get_unallocated_pl(cls, companies, date):
        """A convenience method to obtain the unallocated profit/loss
        of the previous fiscal years at a given date.

        :param companies:
        :param date:

        Returns a tuple (debit, credit)
        """
        # TODO shoud we include here the accounts of type "unaffected"
        # or leave that to the caller?
        bals = cls._get_balances(cls.MODE_UNALLOCATED, companies, date, date)
        return tuple(map(sum, zip(*bals.values())))  # noqa: B905
