from odoo.fields import Domain

# Default hour per day value. The one should
# only be used when the one from the calendar
# is not available.
HOURS_PER_DAY = 8


def filter_domain_leaf(domain, field_check, field_name_mapping=None):
    """
    filter_domain_lead only keep the leaves of a domain that verify a given check. Logical operators that involves
    a leaf that is undetermined (because it does not pass the check) are ignored.

    each operator is a logic gate:
    - '&' and '|' take two entries and can be ignored if one of them (or the two of them) is undetermined
    -'!' takes one entry and can be ignored if this entry is undetermined

    params:
        - domain: the domain that needs to be filtered
        - field_check: the function that the field name used in the leaf needs to verify to keep the leaf
        - field_name_mapping: dictionary of the form {'field_name': 'new_field_name', ...}. Occurences of 'field_name'
          in the first element of domain leaves will be replaced by 'new_field_name'. This is usefull when adapting a
          domain from one model to another when some field names do not match the names of the corresponding fields in
          the new model.
    returns: The filtered version of the domain
    """
    field_name_mapping = field_name_mapping or {}

    def adapt_condition(condition, ignored):
        field_name = condition.field_expr
        if not field_check(field_name):
            return ignored
        field_name = field_name_mapping.get(field_name)
        if field_name is None:
            return condition
        return Domain(field_name, condition.operator, condition.value)

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
