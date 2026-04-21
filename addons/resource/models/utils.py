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
