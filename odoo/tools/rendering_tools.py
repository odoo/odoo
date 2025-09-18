import functools
import re
from urllib.parse import quote, urlencode

from dateutil import relativedelta
from markupsafe import Markup

from odoo.tools import safe_eval

INLINE_TEMPLATE_REGEX = re.compile(r"\{\{(.+?)(\|\|\|\s*(.*?))?\}\}")


def relativedelta_proxy(*args, **kwargs):
    # dateutil.relativedelta is an old-style class and cannot be directly
    # instanciated wihtin a jinja2 expression, so a lambda "proxy" is
    # is needed, apparently
    return relativedelta.relativedelta(*args, **kwargs)


template_env_globals = {
    "str": str,
    "quote": lambda s, safe="/:": quote(str(s), safe=safe),
    "urlencode": urlencode,
    "datetime": safe_eval.datetime,
    "len": len,
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "filter": filter,
    "reduce": functools.reduce,
    "map": map,
    "relativedelta": relativedelta.relativedelta,
    "round": round,
    "hasattr": hasattr,
}


def parse_inline_template(text):
    groups = []
    current_literal_index = 0
    for match in INLINE_TEMPLATE_REGEX.finditer(text):
        literal = text[current_literal_index : match.start()]
        expression = match.group(1)
        default = match.group(3)
        groups.append((literal, expression.strip(), default or ""))
        current_literal_index = match.end()

    # string past last regex match
    literal = text[current_literal_index:]
    if literal:
        groups.append((literal, "", ""))

    return groups


def convert_inline_template_to_qweb(template):
    template_instructions = parse_inline_template(template or "")
    preview_markup = []
    for string, expression, default in template_instructions:
        if expression:
            preview_markup.append(
                Markup('{}<t t-out="{}">{}</t>').format(string, expression, default)
            )
        else:
            preview_markup.append(string)
    return Markup("").join(preview_markup)


def render_inline_template(template_instructions, variables):
    results = []
    for string, expression, default in template_instructions:
        results.append(string)

        if expression:
            result = safe_eval.safe_eval(expression, variables) or default
            if result:
                results.append(str(result))

    return "".join(results)


class QWebErrorInfo:
    """Structured context for QWeb rendering errors."""

    def __init__(
        self,
        error: str,
        ref_name: str | int | None,
        ref: int | None,
        path: str | None,
        element: str | None,
        source: list[tuple[int | str, str, str]],
        surrounding: str,
    ):
        self.error = error
        self.template = ref_name
        self.ref = ref
        self.path = path
        self.element = element
        self.source = source
        self.surrounding = surrounding

    def __str__(self):
        info = [self.error]
        if self.template is not None:
            info.append(f"Template: {self.template}")
        if self.ref is not None:
            info.append(f"Reference: {self.ref}")
        if self.path is not None:
            info.append(f"Path: {self.path}")
        if self.element is not None:
            info.append(f"Element: {self.element}")
        if self.source:
            source = "\n          ".join(str(v) for v in self.source)
            info.append(f"From: {source}")
        if self.surrounding:
            info.append(f"QWeb generated code:\n{self.surrounding}")
        return "\n    ".join(info)


class QWebError(Exception):
    """Exception wrapping a QWebErrorInfo with rendering context."""

    def __init__(self, qweb: QWebErrorInfo):
        super().__init__("Error while rendering the template")
        self.qweb = qweb

    def __str__(self):
        return f"{super().__str__()}:\n    {self.qweb}"
