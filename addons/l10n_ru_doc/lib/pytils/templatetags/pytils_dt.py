# -*- coding: utf-8 -*-
# -*- test-case-name: pytils.test.templatetags.test_dt -*-
"""
pytils.dt templatetags for Django web-framework
"""

import time
from django import template, conf
from pytils import dt
from pytils.templatetags import init_defaults

register = template.Library()  #: Django template tag/filter registrator
debug = conf.settings.DEBUG  #: Debug mode (sets in Django project's settings)
show_value = getattr(conf.settings, 'PYTILS_SHOW_VALUES_ON_ERROR', False)  #: Show values on errors (sets in Django project's settings)

default_value, default_uvalue = init_defaults(debug, show_value)

# -- filters --

def distance_of_time(from_time, accuracy=1):
    """
    Display distance of time from current time.

    Parameter is an accuracy level (deafult is 1).
    Value must be numeral (i.e. time.time() result) or
    datetime.datetime (i.e. datetime.datetime.now()
    result).

    Examples::
        {{ some_time|distance_of_time }}
        {{ some_dtime|distance_of_time:2 }}
    """
    try:
        res = dt.distance_of_time_in_words(from_time, accuracy)
    except Exception as err:
        # because filter must die silently
        try:
            default_distance = "%s seconds" % str(int(time.time() - from_time))
        except Exception:
            default_distance = ""
        res = default_value % {'error': err, 'value': default_distance}
    return res

def ru_strftime(date, format="%d.%m.%Y", inflected_day=False, preposition=False):
    """
    Russian strftime, formats date with given format.

    Value is a date (supports datetime.date and datetime.datetime),
    parameter is a format (string). For explainings about format,
    see documentation for original strftime:
    http://docs.python.org/lib/module-time.html

    Examples::
        {{ some_date|ru_strftime:"%d %B %Y, %A" }}
    """
    try:
        res = dt.ru_strftime(format,
                             date,
                             inflected=True,
                             inflected_day=inflected_day,
                             preposition=preposition)
    except Exception as err:
        # because filter must die silently
        try:
            default_date = date.strftime(format)
        except Exception:
            default_date = str(date)
        res = default_value % {'error': err, 'value': default_date}
    return res

def ru_strftime_inflected(date, format="%d.%m.%Y"):
    """
    Russian strftime with inflected day, formats date
    with given format (similar to ru_strftime),
    also inflects day in proper form.

    Examples::
        {{ some_date|ru_strftime_inflected:"in %A (%d %B %Y)"
    """
    return ru_strftime(date, format, inflected_day=True)

def ru_strftime_preposition(date, format="%d.%m.%Y"):
    """
    Russian strftime with inflected day and correct preposition,
    formats date with given format (similar to ru_strftime),
    also inflects day in proper form and inserts correct
    preposition.

    Examples::
        {{ some_date|ru_strftime_prepoisiton:"%A (%d %B %Y)"
    """
    return ru_strftime(date, format, preposition=True)


# -- register filters
register.filter('distance_of_time', distance_of_time)
register.filter('ru_strftime', ru_strftime)
register.filter('ru_strftime_inflected', ru_strftime_inflected)
register.filter('ru_strftime_preposition', ru_strftime_preposition)
