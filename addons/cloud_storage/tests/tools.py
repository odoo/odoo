# Part of Odoo. See LICENSE file for full copyright and licensing details.

def filter_by_expected(actual, expected):
    """Recursively filters "actual" to retain only keys/elements defined in "expected"."""
    if isinstance(actual, dict) and isinstance(expected, dict):
        return {k: filter_by_expected(actual[k], expected[k]) for k in expected if k in actual}
    elif isinstance(actual, list) and isinstance(expected, list):
        return [filter_by_expected(a, e) for a, e in zip(actual, expected)]
    return actual
