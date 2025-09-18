"""Script-safe JSON encoding utilities.

Provides JSON encoding that is safe for use in HTML <script> tags,
preventing XSS attacks while maintaining valid JSON.
"""

__all__ = [
    "JSON_SCRIPTSAFE_MAPPER",
    "ScriptSafe",
    "ScriptSafeJSON",
    "scriptsafe",
]

import json as json_
import re

import markupsafe

# Character mappings for script-safe JSON encoding
# These characters need special handling when JSON is embedded in HTML
JSON_SCRIPTSAFE_MAPPER = {
    "&": r"\u0026",
    "<": r"\u003c",
    ">": r"\u003e",
    "\u2028": r"\u2028",  # Line separator
    "\u2029": r"\u2029",  # Paragraph separator
}


class ScriptSafe(str):
    """A string subclass that escapes HTML-unsafe characters for script safety.

    When converted to HTML (via __html__), this class escapes characters that
    could break out of script contexts or cause XSS vulnerabilities.
    """

    def __html__(self):
        """Return HTML-safe version of the JSON string.

        Replacement can be done straight in the serialized JSON as the
        problematic characters are not JSON metacharacters (and can thus
        only occur in strings).
        """
        return markupsafe.Markup(
            re.sub(
                r"[<>&\u2028\u2029]",
                lambda m: JSON_SCRIPTSAFE_MAPPER[m[0]],
                self,
            )
        )


class ScriptSafeJSON:
    r"""JSON encoder that produces script-safe output.

    JSON used as JS in HTML (script tags) is problematic: <script>
    tags are a special context which only waits for </script> but doesn't
    interpret anything else. This means standard HTML escaping does not
    work (it breaks double quotes, and e.g. `<` will become `&lt;` *in
    the resulting JSON/JS* not just inside the page).

    However, failing to escape embedded JSON means the JSON strings could
    contain `</script>` and thus become XSS vectors.

    The solution is to use JSON-level unicode escapes for HTML-unsafe
    characters (e.g. "<" -> "\\u003C"). This removes the XSS issue without
    breaking the JSON, and there is no difference to the end result once
    it's been parsed back from JSON. So it will work properly even for
    HTML attributes or raw text.

    Also handles U+2028 and U+2029 as these are interpreted as newlines
    in JavaScript but not in JSON, which could lead to issues.

    .. warning::

        Except inside <script> elements, this should be escaped following
        the normal rules of the containing format.

    Example::

        >>> scriptsafe.dumps({'message': '<script>alert(1)</script>'})
        '{"message": "\\u003cscript\\u003ealert(1)\\u003c/script\\u003e"}'

    See: https://code.djangoproject.com/ticket/17419#comment:27
    """

    def loads(self, *args, **kwargs):
        """Decode JSON string to Python object."""
        return json_.loads(*args, **kwargs)

    def dumps(self, *args, **kwargs):
        """Encode Python object to script-safe JSON string."""
        return ScriptSafe(json_.dumps(*args, **kwargs))


# Default instance for convenient access
scriptsafe = ScriptSafeJSON()
