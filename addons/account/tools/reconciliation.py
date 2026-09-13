from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


def amount_range_after_rate(currency_from, currency_to, amount, rate):
    if not rate:
        return 0.0, 0.0, 0.0
    half_rounding = currency_from.rounding / 2
    return (
        currency_to.round((amount - half_rounding) * rate),
        currency_to.round(amount * rate),
        currency_to.round((amount + half_rounding) * rate),
    )


def pick_reconciliation_currency(
    debit_currency,
    credit_currency,
    company_currency,
    debit_available,
    credit_available,
):
    for currency in (debit_currency, credit_currency):
        if (
            currency != company_currency
            and currency in debit_available
            and currency in credit_available
        ):
            return currency
    return company_currency


def prepare_partial_amounts(context):
    at_par = context["recon_currency"] == context["company_currency"]
    if _debug.logic.enabled:
        _debug.logic(
            "prepare_partial_amounts",
            debit=getattr(context.get("debit_aml"), "id", None),
            credit=getattr(context.get("credit_aml"), "id", None),
            at_par=at_par,
            recon_currency=getattr(context["recon_currency"], "id", None),
        )
    if at_par:
        return _partial_amounts_at_par(context)
    return _partial_amounts_across_rates(context)


def _partial_amounts_at_par(context):
    min_recon_amount = context["min_recon_amount"]
    debit_currency = context["debit_currency"]
    credit_currency = context["credit_currency"]

    if context["exchange_line_mode"]:
        debit_rate = credit_rate = None
    else:
        debit_rate = context["debit_available"].get(debit_currency, {}).get("rate")
        credit_rate = context["credit_available"].get(credit_currency, {}).get("rate")

    if debit_rate:
        partial_debit_amount_currency = min(
            debit_currency.round(debit_rate * min_recon_amount),
            context["remaining_debit_amount_curr"],
        )
    else:
        partial_debit_amount_currency = 0.0
    if credit_rate:
        partial_credit_amount_currency = min(
            credit_currency.round(credit_rate * min_recon_amount),
            -context["remaining_credit_amount_curr"],
        )
    else:
        partial_credit_amount_currency = 0.0

    _debug.logic(
        "at_par_currency_amounts",
        exchange_line_mode=context["exchange_line_mode"],
        partial_amount=min_recon_amount,
        debit_rate=debit_rate,
        credit_rate=credit_rate,
    )
    return {
        "partial_amount": min_recon_amount,
        "partial_debit_amount_currency": partial_debit_amount_currency,
        "partial_credit_amount_currency": partial_credit_amount_currency,
        "partial_debit_amount": None,
        "partial_credit_amount": None,
    }


def _partial_amounts_across_rates(context):
    company_currency = context["company_currency"]
    debit_currency = context["debit_currency"]
    credit_currency = context["credit_currency"]
    min_recon_amount = context["min_recon_amount"]
    debit_rate = context["debit_recon_values"]["rate"]
    credit_rate = context["credit_recon_values"]["rate"]

    debit_range = amount_range_after_rate(
        currency_from=debit_currency,
        currency_to=company_currency,
        amount=min_recon_amount,
        rate=(1 / debit_rate) if debit_rate else 0.0,
    )
    credit_range = amount_range_after_rate(
        currency_from=credit_currency,
        currency_to=company_currency,
        amount=min_recon_amount,
        rate=(1 / credit_rate) if credit_rate else 0.0,
    )
    partial_debit_amount = min(debit_range[1], context["remaining_debit_amount"])
    partial_credit_amount = min(credit_range[1], -context["remaining_credit_amount"])
    partial_amount = min(partial_debit_amount, partial_credit_amount)

    if _ranges_overlap(
        company_currency,
        partial_debit_amount,
        partial_credit_amount,
        debit_range,
        credit_range,
    ):
        partial_amount = min(
            context["remaining_debit_amount"], -context["remaining_credit_amount"]
        )
        _debug.logic("rate_ranges_overlap_snapped", partial_amount=partial_amount)
        partial_debit_amount = partial_amount
        partial_credit_amount = partial_amount

    _debug.logic(
        "across_rates_amounts",
        partial_amount=partial_amount,
        partial_debit_amount=partial_debit_amount,
        partial_credit_amount=partial_credit_amount,
    )
    return {
        "partial_amount": partial_amount,
        "partial_debit_amount_currency": (
            partial_amount if debit_currency == company_currency else min_recon_amount
        ),
        "partial_credit_amount_currency": (
            partial_amount if credit_currency == company_currency else min_recon_amount
        ),
        "partial_debit_amount": partial_debit_amount,
        "partial_credit_amount": partial_credit_amount,
    }


def _ranges_overlap(
    company_currency, debit_amount, credit_amount, debit_range, credit_range
):
    def within(amount, low, high):
        return (
            company_currency.compare_amounts(amount, high) <= 0
            and company_currency.compare_amounts(amount, low) >= 0
        )

    return within(debit_amount, credit_range[0], credit_range[2]) and within(
        credit_amount, debit_range[0], debit_range[2]
    )


def group_lines_by_matching_number(partial_edges):
    parent = {}
    component_size = {}
    component_number = {}

    def find(line_id):
        root_id = line_id
        while parent[root_id] != root_id:
            root_id = parent[root_id]
        while parent[line_id] != line_id:
            next_id = parent[line_id]
            parent[line_id] = root_id
            line_id = next_id
        return root_id

    for partial_id, debit_id, credit_id in partial_edges:
        for line_id in (debit_id, credit_id):
            if line_id not in parent:
                parent[line_id] = line_id
                component_size[line_id] = 1
                component_number[line_id] = partial_id

        debit_root = find(debit_id)
        credit_root = find(credit_id)
        if debit_root == credit_root:
            component_number[debit_root] = min(component_number[debit_root], partial_id)
            continue

        if component_size[debit_root] < component_size[credit_root]:
            debit_root, credit_root = credit_root, debit_root
        parent[credit_root] = debit_root
        component_size[debit_root] += component_size.pop(credit_root)
        component_number[debit_root] = min(
            component_number[debit_root],
            component_number.pop(credit_root),
            partial_id,
        )

    number2lines = {}
    for line_id in parent:
        root_id = find(line_id)
        number2lines.setdefault(component_number[root_id], []).append(line_id)
    _debug.pipeline(
        "matching_numbers_grouped",
        lines=len(parent),
        components=len(number2lines),
    )
    return number2lines
