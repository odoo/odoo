# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import dateutil.relativedelta as relativedelta
import functools
import re

from markupsafe import Markup
from werkzeug import urls

from odoo.tools import safe_eval

INLINE_TEMPLATE_REGEX = re.compile(r"\{\{(.+?)(\|\|\|\s*(.*?))?\}\}")

def relativedelta_proxy(*args, **kwargs):
    # dateutil.relativedelta is an old-style class and cannot be directly
    # instanciated wihtin a jinja2 expression, so a lambda "proxy" is
    # is needed, apparently
    return relativedelta.relativedelta(*args, **kwargs)

template_env_globals = {
    'str': str,
    'quote': urls.url_quote,
    'urlencode': urls.url_encode,
    'datetime': safe_eval.datetime,
    'len': len,
    'abs': abs,
    'min': min,
    'max': max,
    'sum': sum,
    'filter': filter,
    'reduce': functools.reduce,
    'map': map,
    'relativedelta': relativedelta.relativedelta,
    'round': round,
    'hasattr': hasattr,
}

def parse_inline_template(text):
    groups = []
    current_literal_index = 0
    for match in INLINE_TEMPLATE_REGEX.finditer(text):
        literal = text[current_literal_index:match.start()]
        expression = match.group(1)
        default = match.group(3)
        groups.append((literal, expression.strip(), default or ''))
        current_literal_index = match.end()

    # string past last regex match
    literal = text[current_literal_index:]
    if literal:
        groups.append((literal, '', ''))

    return groups

def convert_inline_template_to_qweb(template):
    template_instructions = parse_inline_template(template or '')
    preview_markup = []
    for string, expression, default in template_instructions:
        if expression:
            preview_markup.append(Markup('{}<t t-out="{}">{}</t>').format(string, expression, default))
        else:
            preview_markup.append(string)
    return Markup('').join(preview_markup)

def render_inline_template(template_instructions, variables):
    results = []
    for string, expression, default in template_instructions:
        results.append(string)

        if expression:
            result = safe_eval.safe_eval(expression, variables) or default
            if result:
                results.append(str(result))

    return ''.join(results)
