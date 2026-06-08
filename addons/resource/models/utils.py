import math
from dateutil.relativedelta import relativedelta
from odoo.fields import Domain, parse_field_expr

# Default hour per day value. The one should
# only be used when the one from the calendar
# is not available.
HOURS_PER_DAY = 8


def filter_map_domain(domain, map_function) -> Domain:
    """
    Applies map_function to each condition in the domain. Filters out the domain
    condition if map_function returns None for it.

    :param domain: The original domain to process. Remains unmodified.
    :param map_function: A callable that takes a condition and returns either:
        - A modified Domain, or
        - None (discards the condition).
    :return: A new domain containing only the transformed conditions.
    """
    def adapt_condition(condition, ignored):
        mapped_condition = map_function(condition)
        if mapped_condition is None:
            return ignored
        assert isinstance(
            mapped_condition,
            Domain,
        ), f"map_function() returned {mapped_condition} instead of <Domain | None>"
        return mapped_condition

    def adapt_domain(domain: Domain, ignored) -> Domain:
        if hasattr(domain, 'OPERATOR'):
            if domain.OPERATOR in ('&', '|'):
                domain = domain.apply(adapt_domain(d, domain.ZERO) for d in domain.children)
            elif domain.OPERATOR == '!':
                domain = ~adapt_domain(~domain, ~ignored)
            else:
                assert False, "domain.OPERATOR = {domain.OPEATOR!r} unhandled"
        else:
            domain = domain.map_conditions(lambda condition: adapt_condition(condition, ignored))
        return ignored if domain.is_true() or domain.is_false() else domain

    domain = Domain(domain)
    if domain.is_false():
        return domain
    return adapt_domain(domain, ignored=Domain.TRUE)


def extract_comodel_domain(
    model,
    domain,
    field_expr: str,
):
    """
    Converts a domain to make it usable on the comodel pointed to by `field_expr`

    :param model: The model on which the domain was originally meant for. Usually `self`
    :param domain: The domain we want to convert
    :param field_expr: The field pointing to the comodel we want to translate the domain for.
        e.g.: "employee_id"
    :return: The converted domain, with only the fields meant for the comodel.
        The domain's fields are converted for use on that comodel.
    """
    domain = Domain(domain).optimize_full(model)
    field_name, rest = parse_field_expr(field_expr)
    field = model._fields[field_name]
    if field.related:
        suffix = f'.{rest}' if rest else ''
        return extract_comodel_domain(model, domain, field.related + suffix)

    def _convert_field(condition):
        if (
            hasattr(condition, 'field_expr')
            and condition.field_expr == field_name
        ):
            return Domain('id', condition.operator, condition.value)
        return None

    domain = filter_map_domain(domain, _convert_field)
    comodel = model.env[field.comodel_name]
    if rest:
        return extract_comodel_domain(comodel, domain, rest)
    return domain.optimize_full(comodel)


def get_color_from_code(color, is_open_shift):
    """Take a color code from Odoo's Kanban view and returns an hex code compatible with the fullcalendar library"""
    # if the shift is an open shift, we use the '80' affix at the end of the hex code to modify the transparency
    if is_open_shift:
        switch_color = {
            0: '#00878480',   # No color (doesn't work actually...)
            1: '#EE4B3980',   # Red
            2: '#F2964880',   # Orange
            3: '#F4C60980',   # Yellow
            4: '#55B7EA80',   # Light blue
            5: '#71405B80',   # Dark purple
            6: '#E8686980',   # Salmon pink
            7: '#00878480',   # Medium blue
            8: '#26728380',   # Dark blue
            9: '#BF125580',   # Fushia
            10: '#2BAF7380',  # Green
            11: '#8754B080',  # Purple
        }
    else:
        switch_color = {
            0: '#008784',   # No color (doesn't work actually...)
            1: '#EE4B39',   # Red
            2: '#F29648',   # Orange
            3: '#F4C609',   # Yellow
            4: '#55B7EA',   # Light blue
            5: '#71405B',   # Dark purple
            6: '#E86869',   # Salmon pink
            7: '#008784',   # Medium blue
            8: '#267283',   # Dark blue
            9: '#BF1255',   # Fushia
            10: '#2BAF73',  # Green
            11: '#8754B0',  # Purple
        }
    return switch_color[color]


def get_light_color(color, factor, is_open_shift):
    factor = max(0.0, min(factor, 1.0))
    color = get_color_from_code(color, is_open_shift)

    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)

    r = round(r + (255 - r) * factor)
    g = round(g + (255 - g) * factor)
    b = round(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def extended_gcd(a, b):
    """Extended Euclidean Algorithm: compute the greatest common divisor of
    ``a`` and ``b`` together with the Bézout coefficients.

    Returns a tuple ``(gcd, x, y)`` such that ``a * x + b * y == gcd``, where
    ``gcd`` is the greatest common divisor of ``a`` and ``b``. The Bézout
    coefficients ``x`` and ``y`` are what allow the caller to solve the linear
    congruences used to detect when two periodic recurrences fall on the same
    day (see :func:`get_collision_new_rucurrency`).

    Example::

        >>> extended_gcd(12, 18)
        (6, -1, 1)  # 12 * -1 + 18 * 1 == 6
        >>> extended_gcd(3, 4)
        (1, -1, 1)  # 3 * -1 + 4 * 1 == 1
    """
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y


def get_collision_new_rucurrency(atti, attj):
    """Find the first date on which two periodic recurrences happen on the same day.

    Each argument is a recurrence described by a dict with:

    - ``date``: the date of its first occurrence;
    - ``period``: the number of days between two consecutive occurrences;
    - ``excluded_ocurrences``: a set of date strings on which the occurrence is skipped;
    - ``until``: the last date the recurrence may occur on.

    The two recurrences collide on a common day only if the offset between their
    start dates is a multiple of ``gcd(period_i, period_j)``; otherwise they can
    never align and ``None`` is returned. When they can align, the Chinese
    Remainder Theorem (solved via the Extended Euclidean Algorithm,
    :func:`extended_gcd`) gives the first colliding date, which is then advanced
    to fall within both ranges and to skip any excluded occurrence.

    Mathematical breakdown
    ----------------------
    An occurrence of recurrence ``i`` lands on day ``d`` iff there is an integer
    ``n_i >= 0`` with ``d = date_i + n_i * period_i``. A collision is a day ``d``
    reached by both recurrences, i.e. a solution of the system of congruences::

        d ≡ date_i  (mod period_i)
        d ≡ date_j  (mod period_j)

    Writing ``p = period_i``, ``q = period_j`` and ``delta = date_j - date_i``
    (counted in days), substituting ``d`` yields the linear Diophantine equation::

        n_i * p - n_j * q = delta

    1. **Solvability.** Such ``(n_i, n_j)`` exist iff ``gcd(p, q)`` divides
       ``delta``. This is the early-exit test ``delta % gcd != 0 -> None``.

    2. **A particular solution.** The Extended Euclidean Algorithm returns
       ``x0`` with ``p * x0 + q * (...) = gcd(p, q)``. Scaling Bézout's identity
       by ``delta / gcd`` gives a valid count for the first recurrence::

           n_i = (delta * x0 / gcd)  (mod q / gcd)

       reduced mod ``q / gcd`` to pick the smallest non-negative one. The
       collision date is then ``date_i + n_i * p``.

    3. **Combined period.** Once aligned, both recurrences realign every
       ``lcm(p, q)`` days, so the collisions themselves form a recurrence of
       period ``new_period = lcm(p, q)``.

    4. **Clamping.** The first collision date may fall before the later of the
       two start dates (the congruence solution can be "in the past"); it is
       pushed forward by whole ``new_period`` steps until it is ``>=
       max(date_i, date_j)``, and again until it is not an excluded occurrence.
       If it ends up past ``min(until_i, until_j)``, there is no usable
       collision and ``None`` is returned.

    Returns a tuple ``(new_period, new_date, new_excluded, new_until)`` describing
    the merged recurrence of the collisions, or ``None`` if the two recurrences
    never collide within their bounds.

    Examples::

        # Every 2 days from Jan 1st vs every 3 days from Jan 2nd:
        # they first coincide on Jan 7th, then every lcm(2, 3) = 6 days.
        atti = {'date': date(2024, 1, 1), 'period': 2, 'until': date(2024, 2, 1), 'excluded_ocurrences': set()}
        attj = {'date': date(2024, 1, 2), 'period': 3, 'until': date(2024, 2, 1), 'excluded_ocurrences': set()}
        get_collision_new_rucurrency(atti, attj)  # -> (6, date(2024, 1, 7), set(), date(2024, 2, 1))

        # Every 4 days from Jan 1st vs every 4 days from Jan 2nd:
        # the 1-day offset is not a multiple of gcd(4, 4) = 4, so they never align.
        atti = {'date': date(2024, 1, 1), 'period': 4, 'until': date(2024, 2, 1), 'excluded_ocurrences': set()}
        attj = {'date': date(2024, 1, 2), 'period': 4, 'until': date(2024, 2, 1), 'excluded_ocurrences': set()}
        get_collision_new_rucurrency(atti, attj)  # -> None
    """
    gcd, x0, _ = extended_gcd(atti['period'], attj['period'])
    delta_dates = (attj['date'] - atti['date']).days
    if delta_dates % gcd != 0:
        return None

    new_period = math.lcm(atti['period'], attj['period'])
    n_i_colide = (delta_dates * x0 // gcd) % (attj['period'] // gcd)
    new_date = relativedelta(days=atti['period'] * n_i_colide) + atti['date']
    start_date_max = max(atti['date'], attj['date'])
    if new_date < start_date_max:
        diff_days = (start_date_max - new_date).days
        nb_jumps = (diff_days + new_period - 1) // new_period
        new_date += relativedelta(days=nb_jumps * new_period)

    new_excluded = atti['excluded_ocurrences'] | attj['excluded_ocurrences']
    new_until = min(atti['until'], attj['until'])
    while str(new_date) in new_excluded:
        new_date += relativedelta(days=new_period)

    if new_date > new_until:
        return None

    return new_period, new_date, new_excluded, new_until
