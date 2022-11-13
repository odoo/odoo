# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.osv.expression import normalize_domain, Domain, NOT_OPERATOR, DOMAIN_OPERATORS

def filter_domain_leaf(domain, leaf_check):
    """
    filter_domain_leaf only keep the leaves of a domain that verify a given check. Logical operators that involves
    a leaf that is undetermined (because it does not pass the check) are ignored.

    each operator is a logic gate:
    - '&' and '|' take two entries and can be ignored if one of them (or the two of them) is undetermined
    -'!' takes one entry and can be ignored if this entry is undetermined

    params:
        - domain: the domain that needs to be filtered
        - leaf_check: the function that the field used in the leaf needs to verify to keep the leaf
    returns: The filtered version of the domain
    """
    undetermined = object()
    def _transform(node, model):
        field = node.field
        if field:
            return None if leaf_check(field) else undetermined
        if hasattr(node, 'children') and any(c == undetermined for c in node.children):
            return type(node)(node.zero if c == undetermined else c for c in node.children)
        if getattr(node, 'child', None) == undetermined:
            return undetermined
        return None

    if isinstance(domain, Domain):
        # XXX could always use this
        return domain.transform_domain(_transform)
    def _filter_domain_leaf_recursive(domain, leaf_check, operator=False):
        """
        return domain, rest_domain -> rest_domain should be empty if the operation is finished
        """
        if len(domain) == 0:
            return ([], [])
        if not operator:
            first_elem = domain[0]
            if first_elem not in DOMAIN_OPERATORS: #End of a current leaf
                return ([], domain[1:]) if not leaf_check(first_elem[0]) else ([first_elem], domain[1:])
            operator = first_elem
            domain = domain[1:]

        leaf_1, rest_domain = _filter_domain_leaf_recursive(domain, leaf_check)
        if operator == NOT_OPERATOR:
            return ([operator, *leaf_1], rest_domain) if leaf_1 else ([], rest_domain)
        leaf_2, rest_domain = _filter_domain_leaf_recursive(rest_domain, leaf_check)
        if leaf_1 == [] or leaf_2 == []:
            return ((leaf_1 or leaf_2), rest_domain)
        return  ([operator, *leaf_1, *leaf_2], rest_domain)

    domain = normalize_domain(domain)
    operator = domain[0] if len(domain) > 1 else False
    domain = domain[1:] if len(domain) > 1 else domain
    return _filter_domain_leaf_recursive(domain, leaf_check, operator=operator)[0]
