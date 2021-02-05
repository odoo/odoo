# -*- coding: utf-8 -*-
"""
Pytils templatetags for Django web-framework
"""

# Если отладка, то показываем 'unknown+сообщение об ошибке'.
# Если отладка выключена, то можно чтобы при ошибках показывалось
# значение, переданное фильтру (PYTILS_SHOW_VALUES_ON_ERROR=True)
# либо пустая строка.
def init_defaults(debug, show_value):
    if debug:
        default_value = "unknown: %(error)s"
        default_uvalue = u"unknown: %(error)s"
    elif show_value:
        default_value = "%(value)s"
        default_uvalue = u"%(value)s"
    else:
        default_value = ""
        default_uvalue = u""
    return default_value, default_uvalue
