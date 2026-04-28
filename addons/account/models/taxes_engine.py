from odoo.tools import float_round


# -------------------------------------------------------------------------
# UTILS
# -------------------------------------------------------------------------


class Compute:
    def __init__(self, unpack):
        super().__init__()
        self._result = None
        self._unpack = unpack

    def is_set(self):
        return self._result is not None

    def value(self):
        if not self.is_set():
            self._unpack()
        return self._result

    def set(self, result):
        self._result = result


def distribute_amount_to(amount, factors, rounding=None):
    factors = [
        {
            **factor,
            'source': factor,
            'index': index,
            'norm_factor': abs(factor['factor']),
            'amount': 0.0,
        }
        for index, factor in enumerate(factors)
    ]
    factors.sort(key=lambda x: x['norm_factor'], reverse=True)
    total_factor = sum(factor['norm_factor'] for factor in factors)
    if not total_factor:
        return factors

    for factor in factors:
        factor['norm_factor'] /= total_factor

    amount_sign = -1 if amount < 0.0 else 1
    amount = abs(amount)

    if rounding:
        nb_of_errors = round(abs(amount / rounding))
        remaining_errors = nb_of_errors

        for factor in factors:
            if not remaining_errors:
                break

            norm_factor = factor['norm_factor']
            nb_of_amount_to_distribute = min(
                round(norm_factor * nb_of_errors),
                remaining_errors,
            )

            remaining_errors -= nb_of_amount_to_distribute
            factor['amount'] += amount_sign * nb_of_amount_to_distribute * rounding

        # Distribute the remaining cents across the factors.
        # There are sorted by the biggest first.
        # Since the factors are normalized, the residual number of cents can't be higher than the number of factors.
        for index in range(remaining_errors):
            factors[index]['amount'] += amount_sign * rounding
    else:
        # Distribute using the factor first.
        for factor in factors:
            norm_factor = factor['norm_factor']
            amount_to_distribute = amount_sign * norm_factor * amount
            factor['amount'] += amount_to_distribute

    return factors

def distribute_amount_by_sign(sum_amount, sum_plus_amount, sum_neg_amount, rounding):
    if sum_amount > 0:
        round_sum_plus_amount = float_round(sum_plus_amount, precision_rounding=rounding)
        round_sum_neg_amount = float_round(sum_amount - round_sum_plus_amount, precision_rounding=rounding)
    elif sum_amount < 0:
        round_sum_neg_amount = float_round(sum_neg_amount, precision_rounding=rounding)
        round_sum_plus_amount = float_round(sum_amount - round_sum_neg_amount, precision_rounding=rounding)
    else:
        round_sum_plus_amount = float_round(sum_plus_amount, precision_rounding=rounding)
        round_sum_neg_amount = float_round(sum_neg_amount, precision_rounding=rounding)
    return round_sum_plus_amount, round_sum_neg_amount

def sum_and_distribute_amounts_to(amounts, factors, rounding=None, round_distr=True):
    factors = [
        {
            **factor,
            'source': factor,
            'amount': 0.0,
        }
        for factor in factors
    ]
    plus_factors = [x for x in factors if x['factor'] >= 0]
    neg_factors = [x for x in factors if x['factor'] < 0]
    sum_plus_factor = sum(x['factor'] for x in plus_factors)
    sum_neg_factor = sum(x['factor'] for x in neg_factors)
    abs_sum_factor = abs(sum_plus_factor + sum_neg_factor)

    len_amounts = len(amounts)
    if len_amounts == 1 and len_amounts != len(factors) and abs_sum_factor:
        abs_amount = abs(amounts[0])
        amounts = [abs_amount * sum_plus_factor / abs_sum_factor, abs_amount * sum_neg_factor / abs_sum_factor]

    sum_plus_amount = sum(x for x in amounts if x >= 0)
    sum_neg_amount = sum(x for x in amounts if x < 0)
    distr_rounding = rounding if round_distr else None

    sum_amount = sum(amounts)
    if rounding:
        sum_amount = float_round(sum_amount, precision_rounding=rounding)

    if not round_distr or not rounding:
        for factor in distribute_amount_to(sum_plus_amount, plus_factors, rounding=distr_rounding):
            factor['source']['amount'] += factor['amount']
        for factor in distribute_amount_to(sum_neg_amount, neg_factors, rounding=distr_rounding):
            factor['source']['amount'] += factor['amount']
        return factors

    round_sum_plus_amount, round_sum_neg_amount = distribute_amount_by_sign(sum_amount, sum_plus_amount, sum_neg_amount, rounding)
    for factor in distribute_amount_to(round_sum_plus_amount, plus_factors, rounding=distr_rounding):
        factor['source']['amount'] += factor['amount']
    for factor in distribute_amount_to(round_sum_neg_amount, neg_factors, rounding=distr_rounding):
        factor['source']['amount'] += factor['amount']
    return factors
