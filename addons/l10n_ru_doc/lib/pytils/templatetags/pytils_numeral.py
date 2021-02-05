# -*- coding: utf-8 -*-
# -*- test-case-name: pytils.test.templatetags.test_numeral -*-
"""
pytils.numeral templatetags for Django web-framework
"""

from django import template, conf

from pytils import numeral
from pytils.templatetags import init_defaults
from pytils.third import six

try:
    # Django 1.4+
    from django.utils.encoding import smart_text
except ImportError:
    from django.utils.encoding import smart_unicode
    smart_text = smart_unicode

register = template.Library()  #: Django template tag/filter registrator
encoding = conf.settings.DEFAULT_CHARSET  #: Current charset (sets in Django project's settings)
debug = conf.settings.DEBUG  #: Debug mode (sets in Django project's settings)
show_value = getattr(conf.settings, 'PYTILS_SHOW_VALUES_ON_ERROR', False)  #: Show values on errors (sets in Django project's settings)

default_value, default_uvalue = init_defaults(debug, show_value)

# -- filters

def choose_plural(amount, variants):
    """
    Choose proper form for plural.

    Value is a amount, parameters are forms of noun.
    Forms are variants for 1, 2, 5 nouns. It may be tuple
    of elements, or string where variants separates each other
    by comma.

    Examples::
        {{ some_int|choose_plural:"пример,примера,примеров" }}
    """
    try:
        if isinstance(variants, six.string_types):
            uvariants = smart_text(variants, encoding)
        else:
            uvariants = [smart_text(v, encoding) for v in variants]
        res = numeral.choose_plural(amount, uvariants)
    except Exception as err:
        # because filter must die silently
        try:
            default_variant = variants
        except Exception:
            default_variant = ""
        res = default_value % {'error': err, 'value': default_variant}
    return res

def get_plural(amount, variants):
    """
    Get proper form for plural and it value.

    Value is a amount, parameters are forms of noun.
    Forms are variants for 1, 2, 5 nouns. It may be tuple
    of elements, or string where variants separates each other
    by comma. You can append 'absence variant' after all over variants

    Examples::
        {{ some_int|get_plural:"пример,примера,примеров,нет примеров" }}
    """
    try:
        if isinstance(variants, six.string_types):
            uvariants = smart_text(variants, encoding)
        else:
            uvariants = [smart_text(v, encoding) for v in variants]
        res = numeral._get_plural_legacy(amount, uvariants)
    except Exception as err:
        # because filter must die silently
        try:
            default_variant = variants
        except Exception:
            default_variant = ""
        res = default_value % {'error': err, 'value': default_variant}
    return res

def rubles(amount, zero_for_kopeck=False):
    """Converts float value to in-words representation (for money)"""
    try:
        res = numeral.rubles(amount, zero_for_kopeck)
    except Exception as err:
        # because filter must die silently
        res = default_value % {'error': err, 'value': str(amount)}
    return res

def in_words(amount, gender=None):
    """
    In-words representation of amount.

    Parameter is a gender: MALE, FEMALE or NEUTER

    Examples::
        {{ some_int|in_words }}
        {{ some_other_int|in_words:FEMALE }}
    """
    try:
        res = numeral.in_words(amount, getattr(numeral, str(gender), None))
    except Exception as err:
        # because filter must die silently
        res = default_value % {'error': err, 'value': str(amount)}
    return res

# -- register filters

register.filter('choose_plural', choose_plural)
register.filter('get_plural', get_plural)
register.filter('rubles', rubles)
register.filter('in_words', in_words)

# -- tags

def sum_string(amount, gender, items):
    """
    in_words and choose_plural in a one flask
    Makes in-words representation of value with
    choosing correct form of noun.

    First parameter is an amount of objects. Second is a
    gender (MALE, FEMALE, NEUTER). Third is a variants
    of forms for object name.

    Examples::
        {% sum_string some_int MALE "пример,примера,примеров" %}
        {% sum_string some_other_int FEMALE "задача,задачи,задач" %}
    """
    try:
        if isinstance(items, six.string_types):
            uitems = smart_text(items, encoding, default_uvalue)
        else:
            uitems = [smart_text(i, encoding) for i in items]
        res = numeral.sum_string(amount, getattr(numeral, str(gender), None), uitems)
    except Exception as err:
        # because tag's renderer must die silently
        res = default_value % {'error': err, 'value': str(amount)}
    return res

# -- register tags

register.simple_tag(sum_string)
