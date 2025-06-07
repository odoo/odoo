# -*- coding: utf-8 -*-
from datetime import date, datetime
import json as json_
import re

import markupsafe
from .func import lazy
from .misc import ReadonlyDict

JSON_SCRIPTSAFE_MAPPER = {
    '&': r'\u0026',
    '<': r'\u003c',
    '>': r'\u003e',
    '\u2028': r'\u2028',
    '\u2029': r'\u2029'
}
class _ScriptSafe(str):
    def __html__(self):
        # replacement can be done straight in the serialised JSON as the
        # problematic characters are not JSON metacharacters (and can thus
        # only occur in strings)
        return markupsafe.Markup(re.sub(
            r'[<>&\u2028\u2029]',
            lambda m: JSON_SCRIPTSAFE_MAPPER[m[0]],
            self,
        ))
class JSON:
    def loads(self, *args, **kwargs):
        return json_.loads(*args, **kwargs)
    def dumps(self, *args, **kwargs):
        """ JSON used as JS in HTML (script tags) is problematic: <script>
        tags are a special context which only waits for </script> but doesn't
        interpret anything else, this means standard htmlescaping does not
        work (it breaks double quotes, and e.g. `<` will become `&lt;` *in
        the resulting JSON/JS* not just inside the page).

        However, failing to escape embedded json means the json strings could
        contains `</script>` and thus become XSS vector.

        The solution turns out to be very simple: use JSON-level unicode
        escapes for HTML-unsafe characters (e.g. "<" -> "\u003C". This removes
        the XSS issue without breaking the json, and there is no difference to
        the end result once it's been parsed back from JSON. So it will work
        properly even for HTML attributes or raw text.

        Also handle U+2028 and U+2029 the same way just in case as these are
        interpreted as newlines in javascript but not in JSON, which could
        lead to oddities and issues.

        .. warning::

            except inside <script> elements, this should be escaped following
            the normal rules of the containing format

        Cf https://code.djangoproject.com/ticket/17419#comment:27
        """
        return _ScriptSafe(json_.dumps(*args, **kwargs))
scriptsafe = JSON()


def json_default(obj):
    from odoo import fields  # noqa: PLC0415
    if isinstance(obj, datetime):
        return fields.Datetime.to_string(obj)
    if isinstance(obj, date):
        return fields.Date.to_string(obj)
    if isinstance(obj, lazy):
        return obj._value
    if isinstance(obj, ReadonlyDict):
        return dict(obj)
    if isinstance(obj, bytes):
        return obj.decode()
    return str(obj)
