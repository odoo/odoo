from odoo.tools.pdf import generic

orig_FloatObject___new__ = generic.FloatObject.__new__

def FloatObject___new__(cls, value="0", context=None):
    # Fix invalid numbers like 0.000000000000-5684342
    # Because some PDF generators are building PDF streams with invalid numbers
    if isinstance(value, bytes) and value[0] != b'-' and b'-' in value:
        value = b'-' + b''.join(value.split(b'-', 1))
    elif isinstance(value, str) and value[0] != '-' and '-' in value:
        value = '-' + ''.join(value.split('-', 1))
    return orig_FloatObject___new__(cls, value, context)


generic.FloatObject.__new__ = FloatObject___new__
