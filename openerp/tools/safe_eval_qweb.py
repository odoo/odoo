# -*- coding: utf-8 -*-
##############################################################################
#    Copyright (C) 2004-2012 OpenERP s.a. (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

"""
safe_eval_qweb - methods intended to provide more restricted alternatives
    to evaluate simple and/or untrusted code, objects and browse record.

Methods in this module are typically used as alternatives to eval() to parse
OpenERP domain strings, conditions and expressions, mostly based on locals
condition/math builtins and browse record values.

Only safe Python attributes of objects may be accessed.

Unsafe / not accepted attributes:
* All "private" attributes (not starting with '_')
* browse
* search
* read
* unlink
* read_group

This is done on purpose: it prevents incidental or malicious execution of
Python code that may break the security of the server.

"""

from urllib import urlencode, quote as quote
import datetime
import dateutil.relativedelta as relativedelta
import logging

# We use a jinja2 sandboxed environment to render qWeb templates.
from jinja2.sandbox import SandboxedEnvironment
from jinja2.exceptions import SecurityError, UndefinedError


_logger = logging.getLogger(__name__)


BUILTINS = {
    'False': False,
    'None': None,
    'True': True,
    'abs': abs,
    'bool': bool,
    'dict': dict,
    'filter': filter,
    'len': len,
    'list': list,
    'map': map,
    'max': max,
    'min': min,
    'reduce': reduce,
    'repr': repr,
    'round': round,
    'set': set,
    'str': str,
    'tuple': tuple,
    'str': str,
    'quote': quote,
    'urlencode': urlencode,
    'datetime': datetime,
    # dateutil.relativedelta is an old-style class and cannot be directly
    # instanciated wihtin a jinja2 expression, so a lambda "proxy" is
    # is needed, apparently.
    'relativedelta': lambda *a, **kw : relativedelta.relativedelta(*a, **kw),
}
UNSAFE = [str("browse"), str("search"), str("read"), str("unlink"), str("read_group")]
SAFE = [str("_name")]


class qWebSandboxedEnvironment(SandboxedEnvironment):
    def is_safe_attribute(self, obj, attr, value):
        if str(attr) in SAFE:
            res = True
        else:
            res = super(qWebSandboxedEnvironment, self).is_safe_attribute(obj, attr, value)
            if str(attr) in UNSAFE or not res:
                raise SecurityError("access to attribute '%s' of '%s' object is unsafe." % (attr,obj))
        return res

def safe_eval_qweb(expr, globals_dict=None, locals_dict=None, mode="eval", nocopy=False):
    if globals_dict is None:
        globals_dict = {}
    if locals_dict is None:
        locals_dict = {}

    if not isinstance(locals_dict, dict):
        _logger.warning("The globals_dict and locals_dict of the dynamic environment "+
            "pass to safe_eval_qweb must be dict")

    context = dict(globals_dict)
    context = dict(locals_dict)
    context.update(BUILTINS)

    for key, val in context.items():
        if str(key).startswith('_'):
            context.pop(key)

    env = qWebSandboxedEnvironment(variable_start_string="${", variable_end_string="}")
    env.globals.update(context)

    # use jinja environment
    return env.compile_expression(expr)()
