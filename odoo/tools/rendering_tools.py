import functools
import numbers
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import quote, urlencode

from dateutil import relativedelta
from lxml import etree, html
from markupsafe import Markup, escape

from odoo.libs.debug_log import DebugLog
from odoo.libs.text import VOID_ELEMENTS
from odoo.tools import safe_eval

_debug = DebugLog(__name__)

INLINE_TEMPLATE_REGEX = re.compile(
    r"\{\{(.+?)(?:\|\|\|\s*((?:\\[\\}]|.)*?))?\}\}", re.DOTALL
)
INLINE_DEFAULT_ESCAPE_RE = re.compile(r"\\([\\}])")


def unescape_inline_default(default: str) -> str:
    return INLINE_DEFAULT_ESCAPE_RE.sub(r"\1", default)


def _template_hasattr(obj: object, name: str) -> bool:
    if name.startswith("__") and name.endswith("__"):
        return False
    return hasattr(obj, name)


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
    "hasattr": _template_hasattr,
}


def parse_inline_template(text: str) -> list[tuple[str, str, str]]:
    groups: list[tuple[str, str, str]] = []
    current_literal_index = 0
    for match in INLINE_TEMPLATE_REGEX.finditer(text):
        literal = text[current_literal_index : match.start()]
        expression = match.group(1)
        default = match.group(2)
        groups.append(
            (literal, expression.strip(), unescape_inline_default(default or ""))
        )
        current_literal_index = match.end()

    literal = text[current_literal_index:]
    if literal:
        groups.append((literal, "", ""))

    return groups


def convert_inline_template_to_qweb(template: str | None) -> Markup:
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


BINARY_TYPES = (bytes, bytearray, memoryview)


def renders_as_no_value(result: object) -> bool:
    if isinstance(result, bool):
        return not result
    if isinstance(result, BINARY_TYPES):
        return True
    return not result and not isinstance(result, numbers.Number)


def render_inline_template(
    template_instructions: list[tuple[str, str, str]],
    variables: dict[str, object],
    format_value: Callable[[object], str] = str,
) -> str:
    results = []
    defaulted = 0  # debuglog
    for string, expression, default in template_instructions:
        results.append(string)

        if expression:
            result = safe_eval.safe_eval(expression, variables)
            if renders_as_no_value(result):
                result = default
                defaulted += 1  # debuglog
            if result != "":
                results.append(format_value(result))

    _debug.perf.count(
        "rendering.inline_template",
        expressions=sum(1 for _, expression, _ in template_instructions if expression),
        defaulted=defaulted,
        variables=len(variables),
    )
    return "".join(results)


class QWebErrorInfo:
    def __init__(
        self,
        error: str,
        ref_name: str | int | None,
        ref: str | int | None,
        path: str | None,
        element: str | None,
        source: list[tuple[int | str, str, str]],
        surrounding: str,
    ) -> None:
        self.error = error
        self.template = ref_name
        self.ref = ref
        self.path = path
        self.element = element
        self.source = source
        self.surrounding = surrounding

    def __str__(self) -> str:
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
    def __init__(self, qweb: QWebErrorInfo) -> None:
        super().__init__("Error while rendering the template")
        self.qweb = qweb

    def __str__(self) -> str:
        return f"{super().__str__()}:\n    {self.qweb}"


class StaticRenderUnsupported(Exception):
    pass


HOLE_OPEN, HOLE_CLOSE = "\ue000", "\ue001"
HOLE_RE = re.compile(f"{HOLE_OPEN}(\\d+){HOLE_CLOSE}")


def escape_static_text(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def serialize_static_tree(tree: etree._Element) -> Markup:
    for element in tree.iter():
        if (
            isinstance(element.tag, str)
            and element.text is None
            and len(element) == 0
            and element.tag.lower() not in VOID_ELEMENTS
        ):
            element.text = ""
    body = html.tostring(tree, encoding="unicode", method="xml")
    return Markup(body.removeprefix("<div>").removesuffix("</div>"))


def compile_static_template(
    tree: etree._Element,
) -> tuple[list[str], list[tuple[str, str]]]:
    holes: list[tuple[str, str]] = []
    for element in list(tree.iter()):
        if not isinstance(element.tag, str) or element.get("t-out") is None:
            continue
        expression = element.get("t-out").strip()
        del element.attrib["t-out"]
        default = escape_static_text((element.text or "").strip())
        holes.append((expression, default))
        element.text = f"{HOLE_OPEN}{len(holes) - 1}{HOLE_CLOSE}"
        if element.tag.lower() == "t":
            element.drop_tag()

    segments = HOLE_RE.split(str(serialize_static_tree(tree)))
    if [int(index) for index in segments[1::2]] != list(range(len(holes))):
        _debug.logic(
            "rendering.static_template_unsupported",
            holes=len(holes),
            markers=len(segments[1::2]),
        )
        raise StaticRenderUnsupported(
            "the template's own text carries this renderer's hole markers"
        )
    _debug.perf.count(
        "rendering.static_template_compiled",
        holes=len(holes),
        segments=len(segments[::2]),
    )
    return segments[::2], holes


def render_static_program(
    segments: list[str],
    holes: list[tuple[str, str]],
    resolve: Callable[[str], Any],
) -> Markup:
    out = [segments[0]]
    for (expression, default), segment in zip(holes, segments[1:], strict=True):
        value = resolve(expression)
        if value is None or value is False:
            out.append(default)
        elif isinstance(value, Markup):
            out.append(str(value))
        else:
            out.append(str(escape(str(value))))
        out.append(segment)
    return Markup("".join(out))
