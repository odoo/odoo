import codecs
import csv
import fnmatch
import functools
import inspect
import io
import json
import locale
import logging
import os
import re
import tarfile
import typing
from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import batched
from pathlib import Path
from tokenize import DEDENT, INDENT, NEWLINE, STRING, generate_tokens
from types import FrameType
from typing import IO, Any

import polib
from babel.messages import extract
from lxml import etree, html
from markupsafe import Markup, escape
from psycopg.types.json import Json

import odoo
import odoo.release
from odoo.exceptions import UserError
from odoo.libs.collections import OrderedSet, ReadonlyDict
from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import SQL

import odoo.addons
from .config import config
from .files import file_open, file_path
from .i18n import format_list
from .locale_utils import get_iso_codes
from .misc import SKIPPED_ELEMENT_TYPES

if typing.TYPE_CHECKING:
    from odoo.api import Environment
    from odoo.db import BaseCursor
    from odoo.orm.fields._field_stubs import TranslateDialect
    from odoo.orm.fields.textual import BaseString

__all__ = [
    "LazyTranslate",
    "_",
    "html_translate",
    "xml_translate",
]

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

PYTHON_TRANSLATION_COMMENT = "odoo-python"

JAVASCRIPT_TRANSLATION_COMMENT = "odoo-javascript"

SKIPPED_ELEMENTS = ("script", "style", "title")

TRANSLATED_ELEMENTS = {
    "abbr",
    "b",
    "bdi",
    "bdo",
    "br",
    "cite",
    "code",
    "data",
    "del",
    "dfn",
    "em",
    "font",
    "i",
    "ins",
    "kbd",
    "keygen",
    "mark",
    "math",
    "meter",
    "output",
    "progress",
    "q",
    "ruby",
    "s",
    "samp",
    "small",
    "span",
    "strong",
    "sub",
    "sup",
    "time",
    "u",
    "var",
    "wbr",
    "text",
    "select",
    "option",
}

TRANSLATED_ATTRS = {
    "string",
    "add-label",
    "help",
    "sum",
    "avg",
    "confirm",
    "placeholder",
    "alt",
    "title",
    "aria-label",
    "aria-keyshortcuts",
    "aria-placeholder",
    "aria-roledescription",
    "aria-valuetext",
    "value_label",
    "data-tooltip",
    "label",
    "confirm-label",
    "confirm-title",
    "cancel-label",
}

TRANSLATED_ATTRS.update({f"t-attf-{attr}" for attr in TRANSLATED_ATTRS})

FIELD_TRANSLATE: dict[str | None, bool | TranslationDialect] = {
    None: False,
    "standard": True,
}


def is_translatable_attrib(key: str | None, node: etree._Element) -> bool:
    if not key:
        return False
    if "t-call" not in node.attrib and key in TRANSLATED_ATTRS:
        return True
    return key.endswith(".translate")


def is_translatable_attrib_value(node: etree._Element) -> bool:
    classes = node.attrib.get("class", "").split(" ")
    return (
        (node.tag == "input" and node.attrib.get("type", "text") == "text")
        and "datetimepicker-input" not in classes
    ) or (
        (node.tag == "input" and node.attrib.get("type") == "hidden")
        and "o_translatable_input_hidden" in classes
    )


def is_translatable_attrib_text(node: etree._Element) -> bool:
    return node.tag == "field" and node.attrib.get("widget", "") == "url"


OWL_TRANSLATED_ATTRS = {
    "alt",
    "aria-label",
    "aria-placeholder",
    "aria-roledescription",
    "aria-valuetext",
    "data-tooltip",
    "label",
    "placeholder",
    "title",
}

avoid_pattern = re.compile(r"\s*<!DOCTYPE", re.IGNORECASE | re.MULTILINE | re.UNICODE)
space_pattern = re.compile(r"[\s\uFEFF]*")

FORMAT_REGEX = re.compile(r"(?:#\{(.+?)\})|(?:\{\{(.+?)\}\})")


def translate_format_string_expression(
    term: str, callback: Callable[[str], str | None]
) -> str | None:
    expressions: dict[str, str] = {}

    def add(exp_py: str) -> str:
        index = len(expressions)
        expressions[str(index)] = exp_py
        return "{{%s}}" % index

    term_without_py = FORMAT_REGEX.sub(lambda g: add(g.group(0)), term)
    translated_value = callback(term_without_py)
    if translated_value:
        return FORMAT_REGEX.sub(
            lambda g: expressions.get(g.group(0)[2:-2], "None"),
            translated_value,
        )
    return None


class _XmlNodeTranslator:
    def __init__(
        self,
        callback: Callable[[str], str | None],
        serialize: Callable[[etree._Element], str],
    ) -> None:
        self.callback = callback
        self.serialize = serialize

    @staticmethod
    def _nonspace(text: str | None) -> bool:
        return bool(text) and not space_pattern.fullmatch(text or "")

    @staticmethod
    def _is_force_inline(node: etree._Element) -> bool:
        return "o_translate_inline" in node.attrib.get("class", "").split()

    def _translatable(self, node: etree._Element, force_inline: bool = False) -> bool:
        force_inline = force_inline or self._is_force_inline(node)
        return (
            (force_inline or node.tag in TRANSLATED_ELEMENTS)
            and not any(
                key.startswith("t-") or key == "groups" or key.endswith(".translate")
                for key in node.attrib
            )
            and all(self._translatable(child, force_inline) for child in node)
        )

    def _has_translatable_attrib(
        self, node: etree._Element, child: etree._Element
    ) -> bool:
        return any(
            val
            and (
                is_translatable_attrib(key, node)
                or (key == "value" and is_translatable_attrib_value(child))
                or (key == "text" and is_translatable_attrib_text(child))
            )
            for key, val in child.attrib.items()
        )

    def _hastext(
        self, node: etree._Element, pos: int = 0, force_inline: bool = False
    ) -> bool:
        force_inline = force_inline or self._is_force_inline(node)
        while True:
            if self._nonspace(node[pos - 1].tail if pos else node.text):
                return True
            if pos >= len(node) or not self._translatable(node[pos], force_inline):
                return False
            child = node[pos]
            if self._has_translatable_attrib(node, child) or self._hastext(
                child, 0, force_inline
            ):
                return True
            pos += 1

    @staticmethod
    def _is_skipped(node: etree._Element) -> bool:
        return bool(
            isinstance(node, SKIPPED_ELEMENT_TYPES)
            or node.tag in SKIPPED_ELEMENTS
            or node.get("t-translation", "").strip() == "off"
            or (
                node.tag == "attribute"
                and node.get("name") not in ("value", "text")
                and not is_translatable_attrib(node.get("name"), node)
            )
            or (node.getparent() is None and avoid_pattern.match(node.text or ""))
        )

    def _translate_run(self, node: etree._Element, pos: int) -> int:
        div = etree.Element("div")
        div.text = (node[pos - 1].tail if pos else node.text) or ""
        while pos < len(node) and self._translatable(
            node[pos], self._is_force_inline(node)
        ):
            div.append(node[pos])

        content = self.serialize(div)[5:-6]
        original = content.strip()
        translated = self.callback(original)
        if translated:
            result = content.replace(original, translated)
            result_elem = parse_html(f"<div>{result}</div>")
            result_elem.tag = "span"
            if (
                self._translatable(result_elem)
                and self._hastext(result_elem)
                and sanitize_translated_fragment(div, result_elem)
            ):
                div = result_elem
                if pos:
                    node[pos - 1].tail = div.text
                else:
                    node.text = div.text

        while len(div) > 0:
            node.insert(pos, div[0])
            pos += 1
        return pos

    def _translate_attribs(self, node: etree._Element) -> None:
        for key, val in node.attrib.items():
            if not self._nonspace(val):
                continue
            if not (
                is_translatable_attrib(key, node)
                or (key == "value" and is_translatable_attrib_value(node))
                or (key == "text" and is_translatable_attrib_text(node))
            ):
                continue
            if key.startswith("t-"):
                value = translate_format_string_expression(val.strip(), self.callback)
            else:
                value = self.callback(val.strip())
            node.set(key, value or val)

    def process(self, node: etree._Element) -> None:
        if self._is_skipped(node):
            return

        pos = 0
        while True:
            if self._hastext(node, pos):
                pos = self._translate_run(node, pos)

            if pos >= len(node):
                break

            self.process(node[pos])
            pos += 1

        self._translate_attribs(node)


def translate_xml_node(
    node: etree._Element,
    callback: Callable[[str], str | None],
    serialize: Callable[[etree._Element], str],
) -> etree._Element:
    _XmlNodeTranslator(callback, serialize).process(node)
    return node


def parse_xml(text: str | bytes) -> etree._Element:
    return etree.fromstring(text)


def serialize_xml(node: etree._Element) -> str:
    return etree.tostring(node, method="xml", encoding="unicode")


MODIFIER_ATTRS = {
    "invisible",
    "readonly",
    "required",
    "column_invisible",
    "attrs",
}

TRANSLATOR_ADDABLE_ATTRS = TRANSLATED_ATTRS | {
    "class",
    "id",
    "style",
    "href",
    "target",
    "rel",
    "lang",
    "dir",
    "colspan",
    "rowspan",
}
TRANSLATOR_ADDABLE_ATTR_PREFIX = "data-oe-"

_TEXT_TAG_PATTERN = re.compile(r"</?([A-Za-z][\w:-]*|!|\?)")


def _iter_term_elements(node: etree._Element) -> Iterator[etree._Element]:
    return (el for el in node.iter() if isinstance(el.tag, str))


def _text_tag_names(node: etree._Element) -> set[str]:
    names: set[str] = set()
    for el in _iter_term_elements(node):
        for text in (el.text, el.tail):
            if text:
                names.update(m.lower() for m in _TEXT_TAG_PATTERN.findall(text))
    return names


def _strip_foreign_attributes(
    orig_node: etree._Element, new_node: etree._Element
) -> None:
    orig_pairs = {
        (key, value)
        for el in _iter_term_elements(orig_node)
        for key, value in el.attrib.items()
    }
    for el in _iter_term_elements(new_node):
        for key in list(el.attrib):
            if (
                key in TRANSLATOR_ADDABLE_ATTRS
                or key.startswith(TRANSLATOR_ADDABLE_ATTR_PREFIX)
                or (key, el.attrib[key]) in orig_pairs
            ):
                continue
            del el.attrib[key]


def sanitize_translated_fragment(
    orig_node: etree._Element, new_node: etree._Element
) -> bool:
    if not _text_tag_names(new_node) <= _text_tag_names(orig_node):
        return False
    _strip_foreign_attributes(orig_node, new_node)
    return True


def xml_term_adapter(term_en: str) -> Callable[[str], str | None]:
    orig_node = parse_xml(f"<div>{term_en}</div>")

    def same_struct_iter(
        left: etree._Element, right: etree._Element
    ) -> Iterator[tuple[etree._Element, etree._Element]]:
        if left.tag != right.tag or len(left) != len(right):
            msg = "Non matching struct"
            raise ValueError(msg)
        yield left, right
        left_iter = left.iterchildren()
        right_iter = right.iterchildren()
        for lc, rc in zip(left_iter, right_iter, strict=False):
            yield from same_struct_iter(lc, rc)

    def adapter(term: str) -> str | None:
        new_node = parse_xml(f"<div>{term}</div>")
        if not sanitize_translated_fragment(orig_node, new_node):
            return None
        try:
            for orig_n, new_n in same_struct_iter(orig_node, new_node):
                # The exclusion below has been swept away twice by commits
                # about something else (fb3c3c9bdbb, 28d2ccec482), each time
                # letting a source `style` overwrite the translation's.
                # `test_sync_xml_inline_modifiers` is what catches the third.
                for k in [k for k in new_n.attrib if k in MODIFIER_ATTRS]:
                    del new_n.attrib[k]
                # A translator-addable attribute belongs to the translation, so
                # the source term must not overwrite one the translator set --
                # nor supply one the translation never carried.
                new_n.attrib.update(
                    (k, v)
                    for k, v in orig_n.attrib.items()
                    if k not in TRANSLATOR_ADDABLE_ATTRS
                    and not k.startswith(TRANSLATOR_ADDABLE_ATTR_PREFIX)
                )
        except ValueError:
            return None

        return serialize_xml(new_node)[5:-6]

    return adapter


_HTML_PARSER = etree.HTMLParser(encoding="utf8")


def parse_html(text: str) -> etree._Element:
    try:
        parse = html.fragment_fromstring(text, parser=_HTML_PARSER)
    except (etree.ParserError, TypeError) as e:
        raise UserError(_("Error while parsing view:\n\n%s") % e) from e
    return parse


def serialize_html(node: etree._Element) -> str:
    return etree.tostring(node, method="html", encoding="unicode")


def _xml_translate(
    callback: Callable[[str], str | None], value: str | None
) -> str | None:
    if not value:
        return value

    try:
        root = parse_xml(value)
        result = translate_xml_node(root, callback, serialize_xml)
        return serialize_xml(result)
    except etree.ParseError:
        root = parse_html("<div>%s</div>" % value)
        result = translate_xml_node(root, callback, serialize_xml)
        return serialize_xml(result)[5:-6]


def xml_term_converter(value: str) -> str:
    div = f"<div>{value}</div>"
    root = etree.fromstring(div, etree.HTMLParser())
    return etree.tostring(root[0][0], encoding="unicode")[5:-6]


def _html_translate(
    callback: Callable[[str], str | None], value: str | None
) -> str | None:
    if not value:
        return value

    try:
        root = parse_html("<div>%s</div>" % value)
        result = translate_xml_node(root, callback, serialize_html)
        value = serialize_html(result)[5:-6].replace("\xa0", "&nbsp;")
    except UserError, ValueError:
        _logger.exception("Cannot translate malformed HTML, using source value instead")

    return value


def html_term_converter(value: str) -> str:
    div = f"<div>{value}</div>"
    root = etree.fromstring(div, etree.HTMLParser())
    return etree.tostring(root[0][0], encoding="unicode", method="html")[5:-6]


def get_text_content(term: str) -> str:
    try:
        content = html.fromstring(term).text_content()
    except etree.ParserError:
        return ""
    return " ".join(content.split())


def is_text(term: str) -> bool:
    return len(html.fromstring(f"<div>{term}</div>")) == 0


@dataclass(frozen=True)
class TranslationDialect:
    name: str
    translate: Callable[[Callable[[str], str | None], str | None], str | None]
    get_text_content: Callable[[str], str]
    term_converter: Callable[[str], str]
    is_text: Callable[[str], bool]
    term_adapter: Callable[[str], Callable[[str], str | None]] | None = None

    def __call__(
        self, callback: Callable[[str], str | None], value: str | None
    ) -> str | None:
        return self.translate(callback, value)

    def __repr__(self) -> str:
        return f"<TranslationDialect {self.name}>"


xml_translate = TranslationDialect(
    name="xml_translate",
    translate=_xml_translate,
    get_text_content=get_text_content,
    term_converter=xml_term_converter,
    is_text=is_text,
    term_adapter=xml_term_adapter,
)

html_translate = TranslationDialect(
    name="html_translate",
    translate=_html_translate,
    get_text_content=get_text_content,
    term_converter=html_term_converter,
    is_text=is_text,
)

FIELD_TRANSLATE["html_translate"] = html_translate
FIELD_TRANSLATE["xml_translate"] = xml_translate


_POSITIONAL_PLACEHOLDER = re.compile(r"%(?!\()")


def _is_iterable_arg(value: object) -> bool:
    return not isinstance(value, (str, bytes)) and isinstance(value, Iterable)


def _materialise(value: object) -> object:
    return list(value) if _is_iterable_arg(value) else value  # type: ignore[call-overload]


def get_translation(module: str, lang: str, source: str, args: tuple | dict) -> str:
    assert lang, "missing language for translation"
    if lang == "en_US":
        translation = source
    else:
        assert module, "missing module name for translation"
        translation = code_translations.get_python_translations(module, lang).get(
            source, source
        )
    if not args:
        return translation
    vals: Collection
    if isinstance(args, dict):
        args = {k: _materialise(v) for k, v in args.items()}
        vals = args.values()
    else:
        args = tuple(_materialise(v) for v in args)
        vals = args

    has_markup = has_lazy = has_iterable = False
    for v in vals:
        if isinstance(v, Markup):
            has_markup = True
        elif isinstance(v, LazyGettext):
            has_lazy = True
        elif _is_iterable_arg(v):
            has_iterable = True
            if not has_markup and any(isinstance(el, Markup) for el in v):
                has_markup = True
        if has_markup and has_lazy and has_iterable:
            break
    if has_markup:
        translation = escape(translation)
    if has_lazy:
        if isinstance(args, dict):
            args = {
                k: v._translate(lang) if isinstance(v, LazyGettext) else v
                for k, v in args.items()
            }
        else:
            args = tuple(
                v._translate(lang) if isinstance(v, LazyGettext) else v for v in args
            )
    if has_iterable:

        def translate_arg(v: Any) -> Any:
            if _is_iterable_arg(v):
                v = [
                    el._translate(lang) if isinstance(el, LazyGettext) else el
                    for el in v
                ]
                if any(isinstance(el, Markup) for el in v):
                    v = [el if isinstance(el, Markup) else escape(el) for el in v]
                    return Markup(format_list(env=None, lst=v, lang_code=lang))
                return format_list(env=None, lst=v, lang_code=lang)
            return v

        if isinstance(args, dict):
            args = {k: translate_arg(v) for k, v in args.items()}
        else:
            args = tuple(translate_arg(v) for v in args)
    try:
        if isinstance(args, dict) and _POSITIONAL_PLACEHOLDER.search(
            translation.replace("%%", "")
        ):
            msg = "translation uses positional placeholders but args is a mapping"
            raise TypeError(msg)
        return translation % args
    except TypeError, ValueError, KeyError:
        bad = translation
        translation = (escape(source) if has_markup else source) % args
        _logger.exception("Bad translation %r for string %r", bad, source)
        _debug.logic(
            "translate.bad_translation_fallback",
            module=module,
            lang=lang,
            source=source,
            mapping=isinstance(args, dict),
        )
    return translation


def get_translated_module(
    arg: str | int | typing.Any,
) -> str:
    if isinstance(arg, str):
        if arg.startswith("odoo.addons."):
            return arg.split(".")[2]
        if "." in arg or not arg:
            return "base"
        else:
            return arg
    else:
        if isinstance(arg, int):
            frame = inspect.currentframe()
            while arg > 0 and frame is not None:
                arg -= 1
                frame = frame.f_back
        else:
            frame = arg
        if not frame:
            return "base"
        if (module_name := frame.f_globals.get("__name__")) and module_name.startswith(
            "odoo.addons."
        ):
            return module_name.split(".")[2]
        path = inspect.getfile(frame)
        from odoo.modules import get_resource_from_path

        path_info = get_resource_from_path(path)
        return path_info.module if path_info else "base"


def _probe(obj: object, name: str) -> Any:
    if obj is None:
        return None
    try:
        return object.__getattribute__(obj, name)
    except AttributeError:
        return None


def _get_cr(frame: FrameType, fallback: BaseCursor | None = None) -> BaseCursor | None:
    if "cr" in frame.f_locals:
        return frame.f_locals["cr"]
    if "cursor" in frame.f_locals:
        return frame.f_locals["cursor"]
    if (local_self := frame.f_locals.get("self")) is not None:
        if (local_env := _probe(local_self, "env")) is not None:
            return _probe(local_env, "cr")
        if (cr := _probe(local_self, "cr")) is not None:
            return cr
    return fallback


def _get_uid(frame: FrameType) -> int | None:
    if "uid" in frame.f_locals:
        return frame.f_locals["uid"]
    if "user" in frame.f_locals:
        try:
            return int(frame.f_locals["user"])
        except TypeError, ValueError:
            pass
    if (local_self := frame.f_locals.get("self")) is not None:
        if (local_env := _probe(local_self, "env")) is not None:
            if uid := _probe(local_env, "uid"):
                return uid
    return None


_LANG_FRAME_SEARCH_DEPTH = 10


def _lang_search_frames(frame: FrameType | None) -> Iterator[FrameType]:
    for _depth in range(_LANG_FRAME_SEARCH_DEPTH):
        if frame is None:
            return
        yield frame
        frame = frame.f_back


def _mapping_lang(candidate: object) -> str:
    if not isinstance(candidate, Mapping):
        return ""
    lang = candidate.get("lang")
    return lang if isinstance(lang, str) else ""


def _get_frame_context_lang(f_locals: Mapping) -> str:
    if lang := _mapping_lang(f_locals.get("context")):
        return lang
    if isinstance(local_kwargs := f_locals.get("kwargs"), Mapping):
        return _mapping_lang(local_kwargs.get("context"))
    return ""


def _get_lang(frame: FrameType | None, default_lang: str = "") -> str:
    frames: list[FrameType] = []
    found_env = False
    for candidate in _lang_search_frames(frame):
        frames.append(candidate)
        f_locals = candidate.f_locals
        if lang := _get_frame_context_lang(f_locals):
            return lang
        local_env = _probe(f_locals.get("self"), "env")
        if local_env:
            found_env = True
            if lang := local_env.lang:
                return lang
    request_env = None
    http = getattr(odoo, "http", None)
    if http and (req := http.request):
        request_env = req.env
    if request_env:
        found_env = True
        if lang := request_env.lang:
            return lang
    request_cr = request_env.cr if request_env else None
    for candidate in frames:
        cr = _get_cr(candidate, request_cr)
        uid = _get_uid(candidate)
        if cr and uid:
            from odoo import api

            found_env = True
            env = api.Environment(cr, uid, {})
            lang = env["res.users"].context_get().get("lang")
            _debug.logic(
                "translate.lang_from_user_context",
                uid=uid,
                lang=lang or None,
                frames_walked=len(frames),
                function=candidate.f_code.co_name,
            )
            if lang:
                return lang
            break
    if default_lang:
        _logger.debug("no translation language detected, fallback to %s", default_lang)
        _debug.logic(
            "translate.lang_defaulted",
            lang=default_lang,
            found_env=found_env,
            frames_walked=len(frames),
        )
        return default_lang
    _logger.log(
        logging.DEBUG if found_env else logging.WARNING,
        "no translation language detected, skipping translation %s",
        frame,
        stack_info=True,
    )
    _debug.logic(
        "translate.lang_not_detected",
        found_env=found_env,
        frames_walked=len(frames),
        function=frame.f_code.co_name if frame else None,
    )
    return ""


def _get_translation_source(
    stack_level: int, module: str = "", lang: str = "", default_lang: str = ""
) -> tuple[str, str]:
    if not (module and lang):
        frame = inspect.currentframe()
        for _index in range(stack_level + 1):
            frame = frame.f_back if frame else None
        lang = lang or _get_lang(frame, default_lang)
    if lang and lang != "en_US":
        return get_translated_module(module or frame), lang
    else:
        return module or "base", "en_US"


def get_text_alias(source: str, /, *args: object, **kwargs: object) -> str:
    assert not (args and kwargs)
    assert isinstance(source, str)
    module, lang = _get_translation_source(1)
    return get_translation(module, lang, source, args or kwargs)


@functools.total_ordering
class LazyGettext:
    __slots__ = ("_args", "_default_lang", "_module", "_source")

    def __init__(
        self,
        source: str,
        /,
        *args: object,
        _module: str = "",
        _default_lang: str = "",
        **kwargs: object,
    ) -> None:
        assert not (args and kwargs)
        assert isinstance(source, str)
        self._source = source
        self._args = args or kwargs
        self._module = get_translated_module(_module or 2)
        self._default_lang = _default_lang

    def _translate(self, lang: str = "") -> str:
        module, lang = _get_translation_source(
            2, self._module, lang, default_lang=self._default_lang
        )
        return get_translation(module, lang, self._source, self._args)

    def __repr__(self) -> str:
        args = {
            "_module": self._module,
            "_default_lang": self._default_lang,
            "_args": self._args,
        }
        return f"_lt({self._source!r}, **{args!r})"

    def __str__(self) -> str:
        return self._translate()

    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError

    def __lt__(self, other: object) -> bool:
        raise NotImplementedError

    def __add__(self, other: object) -> str:
        if isinstance(other, str):
            return self._translate() + other
        elif isinstance(other, LazyGettext):
            return self._translate() + other._translate()
        return NotImplemented

    def __radd__(self, other: object) -> str:
        if isinstance(other, str):
            return other + self._translate()
        return NotImplemented


class LazyTranslate:
    module: str
    default_lang: str

    def __init__(self, module: str, *, default_lang: str = "") -> None:
        self.module = module = get_translated_module(module or 2)
        self.default_lang = default_lang or ("en_US" if module == "base" else "")

    def __call__(self, source: str, *args, **kwargs) -> LazyGettext:
        return LazyGettext(
            source,
            *args,
            **kwargs,
            _module=self.module,
            _default_lang=self.default_lang,
        )


_ = get_text_alias
_lt = LazyGettext


def parse_xmlid(xmlid: str, default_module: str) -> tuple[str, str]:
    split_id = xmlid.split(".", maxsplit=1)
    if len(split_id) == 1:
        return default_module, split_id[0]
    return split_id[0], split_id[1]


def translation_file_reader(
    source: str | IO[bytes], fileformat: str = "po", module: str | None = None
) -> Iterable[dict]:
    if fileformat == "po":
        return PoFileReader(source)
    if isinstance(source, str):
        raise ValueError(f"{fileformat} translations must be read from a stream")
    if fileformat == "csv":
        if module is not None:
            return CSVDataFileReader(source, module)
        return CSVFileReader(source)
    if fileformat == "xml":
        assert module
        return XMLDataFileReader(source, module)
    _logger.info("Bad file format: %s", fileformat)
    raise ValueError(f"Bad file format: {fileformat}")


class CSVFileReader:
    def __init__(self, source: IO[bytes]) -> None:
        _reader = codecs.getreader("utf-8")
        self.source = csv.DictReader(_reader(source), quotechar='"', delimiter=",")
        self.prev_code_src = ""

    def __iter__(self) -> Iterator[dict]:
        for entry in self.source:
            if entry["res_id"] and entry["res_id"].isnumeric():
                entry["res_id"] = int(entry["res_id"])
            elif not entry.get("imd_name"):
                res_id = entry["res_id"]
                if "." not in res_id:
                    msg = (
                        f"Malformed translation row: res_id {res_id!r} is "
                        "neither numeric nor a fully qualified external id "
                        "(module.name)"
                    )
                    raise ValueError(msg)
                entry["module"], entry["imd_name"] = res_id.split(".", 1)
                entry["res_id"] = None
            if entry["type"] == "model" or entry["type"] == "model_terms":
                entry["imd_model"] = entry["name"].partition(",")[0]

            if entry["type"] == "code":
                if entry["src"] == self.prev_code_src:
                    continue
                self.prev_code_src = entry["src"]

            yield entry


class CSVDataFileReader:
    def __init__(self, source: IO[bytes], module: str) -> None:
        _reader = codecs.getreader("utf-8")
        self.module = module
        self.model = Path(source.name).stem.split("-")[0]
        self.source = csv.DictReader(_reader(source), quotechar='"', delimiter=",")
        self.prev_code_src = ""

    def __iter__(self) -> Iterator[dict]:
        translated_fnames = sorted(
            [
                fname.split("@", maxsplit=1)
                for fname in self.source.fieldnames or []
                if "@" in fname
            ],
            key=lambda x: x[1],
        )
        for entry in self.source:
            for fname, lang in translated_fnames:
                module, imd_name = parse_xmlid(entry["id"], self.module)
                yield {
                    "type": "model",
                    "imd_model": self.model,
                    "imd_name": imd_name,
                    "lang": lang,
                    "value": entry[f"{fname}@{lang}"],
                    "src": entry[fname],
                    "module": module,
                    "name": f"{self.model},{fname}",
                }


class XMLDataFileReader:
    def __init__(self, source: IO[bytes], module: str) -> None:
        try:
            tree = etree.parse(source)
        except etree.LxmlSyntaxError:
            _logger.warning("Error parsing XML file %s", source)
            _debug.logic(
                "translate.datafile_unparsable",
                module=module,
                file=getattr(source, "name", None),
            )
            tree = etree.fromstring("<data/>")
        self.source = tree
        self.module = module

    def __iter__(self) -> Iterator[dict]:
        for record in self.source.xpath("//field[contains(@name, '@')]/.."):
            vals = {field.attrib["name"]: field.text for field in record.xpath("field")}
            translated_fnames = sorted(
                [fname.split("@", maxsplit=1) for fname in vals if "@" in fname],
                key=lambda x: x[1],
            )
            for fname, lang in translated_fnames:
                module, imd_name = parse_xmlid(record.attrib["id"], self.module)
                yield {
                    "type": "model",
                    "imd_model": record.attrib["model"],
                    "imd_name": imd_name,
                    "lang": lang,
                    "value": vals[f"{fname}@{lang}"],
                    "src": vals[fname],
                    "module": module,
                    "name": f"{record.attrib['model']},{fname}",
                }


class PoFileReader:
    def __init__(self, source: str | IO[bytes]) -> None:
        def get_pot_path(source_name: str | IO[bytes]) -> str | typing.Literal[False]:
            if isinstance(source_name, str) and source_name.endswith(".po"):
                path = Path(source_name)
                filename = path.parent.parent.name + ".pot"
                pot_path = path.with_name(filename)
                return (pot_path.exists() and str(pot_path)) or False
            return False

        if isinstance(source, str):
            self.pofile = polib.pofile(source)
            pot_path = get_pot_path(source)
        else:
            self.pofile = polib.pofile(source.read().decode())
            pot_path = get_pot_path(getattr(source, "name", ""))

        if pot_path:
            self.pofile.merge(polib.pofile(pot_path))
        _debug.lifecycle(
            "translate.po_read",
            file=source if isinstance(source, str) else getattr(source, "name", None),
            entries=len(self.pofile),
            pot_merged=bool(pot_path),
        )

    def __iter__(self) -> Iterator[dict]:
        for entry in self.pofile:
            if entry.obsolete:
                continue

            comment = entry.comment or ""
            comment_match = re.match(r"(module[s]?): (\w+)", comment)
            entry_module = comment_match.group(2) if comment_match else None
            comments = "\n".join(
                c
                for c in comment.split("\n")
                if not c.startswith(("module:", "modules:"))
            )
            source = entry.msgid
            translation = entry.msgstr
            found_code_occurrence = False
            for occurrence, line_number in entry.occurrences:
                match = re.match(
                    r"(model|model_terms):([\w.]+),([\w]+):(\w+)\.([^ ]+)",
                    occurrence,
                )
                if match:
                    type, model_name, field_name, xmlid_module, xmlid = match.groups()
                    yield {
                        "type": type,
                        "imd_model": model_name,
                        "name": model_name + "," + field_name,
                        "imd_name": xmlid,
                        "res_id": None,
                        "src": source,
                        "value": translation,
                        "comments": comments,
                        "module": xmlid_module,
                    }
                    continue

                match = re.match(r"(code):([\w/.]+)", occurrence)
                if match:
                    type, name = match.groups()
                    if found_code_occurrence:
                        continue
                    found_code_occurrence = True
                    yield {
                        "type": type,
                        "name": name,
                        "src": source,
                        "value": translation,
                        "comments": comments,
                        "res_id": int(line_number) if line_number.isdigit() else 0,
                        "module": entry_module,
                    }
                    continue

                match = re.match(r"(selection):([\w.]+),([\w]+)", occurrence)
                if match:
                    _logger.info("Skipped deprecated occurrence %s", occurrence)
                    _debug.logic(
                        "translate.po_occurrence_skipped",
                        kind="selection",
                        occurrence=occurrence,
                    )
                    continue

                match = re.match(r"(sql_constraint|constraint):([\w.]+)", occurrence)
                if match:
                    _logger.info("Skipped deprecated occurrence %s", occurrence)
                    _debug.logic(
                        "translate.po_occurrence_skipped",
                        kind="constraint",
                        occurrence=occurrence,
                    )
                    continue
                _logger.error("malformed po file: unknown occurrence: %s", occurrence)
                _debug.logic(
                    "translate.po_occurrence_skipped",
                    kind="unknown",
                    occurrence=occurrence,
                )


class _RowWriter(typing.Protocol):
    def write_rows(self, rows: Iterable) -> None: ...


def TranslationFileWriter(
    target: IO[bytes], fileformat: str = "po", lang: str | None = None
) -> _RowWriter:
    if fileformat == "csv":
        return CSVFileWriter(target)

    if fileformat == "po":
        return PoFileWriter(target, lang=lang)

    if fileformat == "tgz":
        return TarFileWriter(target, lang=lang)

    raise ValueError(
        f"Unrecognized extension: must be one of .csv, .po, or .tgz "
        f"(received .{fileformat})."
    )


_writer = codecs.getwriter("utf-8")


class _UnixDialect(csv.excel):
    lineterminator = "\n"


class CSVFileWriter:
    def __init__(self, target: IO[bytes]) -> None:
        self.writer = csv.writer(_writer(target), dialect=_UnixDialect)
        self.writer.writerow(
            ("module", "type", "name", "res_id", "src", "value", "comments")
        )

    def write_rows(self, rows: Iterable) -> None:
        for module, type, name, res_id, src, trad, comments in rows:
            comments = "\n".join(comments)
            self.writer.writerow((module, type, name, res_id, src, trad, comments))


class PoFileWriter:
    def __init__(self, target: IO[bytes], lang: str | None) -> None:
        self.buffer = target
        self.lang = lang
        self.po = polib.POFile()

    def write_rows(self, rows: Iterable) -> None:
        grouped_rows: dict[str, dict[str, Any]] = {}
        modules = set()
        for module, type, name, res_id, src, trad, comments in rows:
            row = grouped_rows.setdefault(src, {})
            row.setdefault("modules", set()).add(module)
            if not row.get("translation") and trad != src:
                row["translation"] = trad
            row.setdefault("tnrs", []).append((type, name, res_id))
            row.setdefault("comments", set()).update(comments)
            modules.add(module)

        for src, row in sorted(grouped_rows.items()):
            if not self.lang or not row.get("translation"):
                row["translation"] = ""
            self.add_entry(
                sorted(row["modules"]),
                sorted(row["tnrs"]),
                src,
                row["translation"],
                sorted(row["comments"]),
            )
        _debug.pipeline(
            "translate.po_written",
            lang=self.lang,
            modules=sorted(modules),
            entries=len(grouped_rows),
            translated=sum(bool(row["translation"]) for row in grouped_rows.values()),
        )

        self.po.header = (
            "Translation of %s.\n"
            "This file contains the translation of the following modules:\n"
            "%s"
            % (
                odoo.release.description,
                "".join("\t* %s\n" % m for m in sorted(modules)),
            )
        )
        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M+0000")
        self.po.metadata = {
            "Project-Id-Version": "%s %s"
            % (odoo.release.description, odoo.release.series),
            "Report-Msgid-Bugs-To": "",
            "POT-Creation-Date": now,
            "PO-Revision-Date": now,
            "Last-Translator": "",
            "Language-Team": "",
            "MIME-Version": "1.0",
            "Content-Type": "text/plain; charset=UTF-8",
            "Content-Transfer-Encoding": "",
            "Plural-Forms": "",
        }

        self.buffer.write(str(self.po).encode())

    def add_entry(
        self,
        modules: list[str],
        tnrs: list,
        source: str,
        trad: str,
        comments: list[str] | None = None,
    ) -> None:
        entry = polib.POEntry(
            msgid=source,
            msgstr=trad,
        )
        plural = (len(modules) > 1 and "s") or ""
        entry.comment = "module%s: %s" % (plural, ", ".join(modules))
        if comments:
            entry.comment += "\n" + "\n".join(comments)
        occurrences: OrderedSet[tuple[str, str | None]] = OrderedSet()
        for type_, *ref in tnrs:
            if type_ == "code":
                fpath, lineno = ref
                name = f"code:{fpath}"
                lineno = "0"
            else:
                field_name, xmlid = ref
                name = f"{type_}:{field_name}:{xmlid}"
                lineno = None
            occurrences.add((name, lineno))
        entry.occurrences = list(occurrences)
        self.po.append(entry)


class TarFileWriter:
    def __init__(self, target: IO[bytes], lang: str | None) -> None:
        self.target = target
        self.lang = lang

    def write_rows(self, rows: Iterable) -> None:
        rows_by_module = defaultdict(list)
        for row in rows:
            module = row[0]
            rows_by_module[module].append(row)

        with tarfile.open(fileobj=self.target, mode="w|gz") as tar:
            for mod, modrows in rows_by_module.items():
                with io.BytesIO() as buf:
                    po = PoFileWriter(buf, lang=self.lang)
                    po.write_rows(modrows)
                    buf.seek(0)

                    ext = "po" if self.lang else "pot"
                    info = tarfile.TarInfo(
                        str(Path(mod, "i18n", f"{self.lang or mod}.{ext}"))
                    )
                    info.size = buf.getbuffer().nbytes

                    tar.addfile(info, fileobj=buf)

        _debug.pipeline(
            "translate.tar_written", lang=self.lang, modules=len(rows_by_module)
        )


def _trans_export(
    reader: TranslationModuleReader | TranslationRecordReader,
    lang: str | None,
    buffer: IO[bytes],
    format: str,
) -> bool:
    if not reader:
        _debug.logic("translate.export_empty", lang=lang, format=format)
        return False
    writer = TranslationFileWriter(buffer, fileformat=format, lang=lang)
    with _debug.perf(
        "translate.export_write",
        lang=lang,
        format=format,
        terms=len(reader._to_translate),
    ):
        writer.write_rows(reader)
    return True


def trans_export(
    lang: str | None,
    modules: list[str],
    buffer: IO[bytes],
    format: str,
    env: Environment,
) -> bool:
    with _debug.perf(
        "translate.export_modules",
        cr=env.cr,
        lang=lang,
        modules=modules,
        format=format,
    ) as span:
        reader = TranslationModuleReader(env.cr, modules=modules, lang=lang)
        span.set(terms=len(reader._to_translate))
    return _trans_export(reader, lang, buffer, format)


def trans_export_records(
    lang: str,
    model_name: str,
    ids: list[int],
    buffer: IO[bytes],
    format: str,
    env: Environment,
) -> bool:
    with _debug.perf(
        "translate.export_records",
        cr=env.cr,
        lang=lang,
        model=model_name,
        records=len(ids),
        format=format,
    ) as span:
        reader = TranslationRecordReader(env.cr, model_name, ids, lang=lang)
        span.set(terms=len(reader._to_translate))
    return _trans_export(reader, lang, buffer, format)


def _push(
    callback: Callable[[str, int], None], term: str | None, source_line: int
) -> None:
    term = (term or "").strip()
    if any(x.isalpha() for x in term):
        callback(term, source_line)


def _extract_translatable_qweb_terms(
    element: etree._Element, callback: Callable[[str, int], None]
) -> None:
    for el in element:
        if isinstance(el, SKIPPED_ELEMENT_TYPES):
            continue
        if (
            el.tag.lower() not in SKIPPED_ELEMENTS
            and "t-js" not in el.attrib
            and not (
                el.tag == "attribute" and not is_translatable_attrib(el.get("name"), el)
            )
            and el.get("t-translation", "").strip() != "off"
        ):
            _push(callback, el.text, el.sourceline)
            is_component = (
                el.tag[0].isupper()
                or "t-component" in el.attrib
                or "t-set-slot" in el.attrib
            )
            for attr in el.attrib:
                if (not is_component and attr in OWL_TRANSLATED_ATTRS) or (
                    is_component and attr.endswith(".translate")
                ):
                    _push(callback, el.attrib[attr], el.sourceline)
            _extract_translatable_qweb_terms(el, callback)
        _push(callback, el.tail, el.sourceline)


def babel_extract_qweb(
    fileobj: IO[bytes], keywords: list, comment_tags: list, options: dict
) -> list[tuple]:
    result: list[tuple] = []

    def handle_text(text: str, lineno: int) -> None:
        result.append((lineno, None, text, []))

    tree = etree.parse(fileobj)
    _extract_translatable_qweb_terms(tree.getroot(), handle_text)
    return result


def extract_formula_terms(formula: str) -> Iterator[str]:
    tokens = generate_tokens(io.StringIO(formula).readline)
    tokens = (token for token in tokens if token.type not in {NEWLINE, INDENT, DEDENT})
    for t1 in tokens:
        if t1.string != "_t":
            continue
        t2 = next(tokens, None)
        if t2 and t2.string == "(":
            t3 = next(tokens, None)
            t4 = next(tokens, None)
            if t4 and t4.string == ")" and t3 and t3.type == STRING:
                yield t3.string[1:][:-1]


def extract_spreadsheet_terms(
    fileobj: IO[bytes], keywords: list, comment_tags: list, options: dict
) -> Iterator[tuple]:
    terms: set[str] = set()
    data = json.load(fileobj)
    for sheet in data.get("sheets", []):
        for cell in sheet["cells"].values():
            content = cell if isinstance(cell, str) else cell.get("content", "")
            if content.startswith("="):
                terms.update(extract_formula_terms(content))
            else:
                markdown_link = re.fullmatch(r"\[(.+)\]\(.+\)", content)
                if markdown_link:
                    terms.add(markdown_link[1])
        for figure in sheet["figures"]:
            if figure["tag"] == "chart":
                title = figure["data"]["title"]
                if isinstance(title, str):
                    terms.add(title)
                elif "text" in title:
                    terms.add(title["text"])
                if "axesDesign" in figure["data"]:
                    terms.update(
                        axes.get("title", {}).get("text", "")
                        for axes in figure["data"]["axesDesign"].values()
                    )
                if "text" in (baselineDescr := figure["data"].get("baselineDescr", {})):
                    terms.add(baselineDescr["text"])
                if "text" in (keyDescr := figure["data"].get("keyDescr", {})):
                    terms.add(keyDescr["text"])
    terms.update(
        global_filter["label"] for global_filter in data.get("globalFilters", [])
    )
    return ((0, None, term, []) for term in terms if any(x.isalpha() for x in term))


class ImdInfo(typing.NamedTuple):
    name: str
    model: str
    res_id: int
    module: str


class TranslationReader:
    def __init__(self, cr: BaseCursor, lang: str | None = None) -> None:
        self._cr = cr
        self._lang = lang or "en_US"
        from odoo import api

        self.env = api.Environment(cr, api.SUPERUSER_ID, {})
        self._to_translate: list = []

    def __bool__(self) -> bool:
        return bool(self._to_translate)

    def __iter__(self) -> Iterator[tuple]:
        for (
            module,
            source,
            name,
            res_id,
            ttype,
            comments,
            _record_id,
            value,
        ) in self._to_translate:
            yield (module, ttype, name, res_id, source, value, comments)

    def _push_translation(
        self,
        module: str,
        ttype: str,
        name: str,
        res_id: str | int | None,
        source: str,
        comments: list | None = None,
        record_id: int | None = None,
        value: str | None = None,
    ) -> None:
        sanitized_term = (source or "").strip()
        if not any(c.isalpha() for c in sanitized_term):
            return
        self._to_translate.append(
            (
                module,
                source,
                name,
                res_id,
                ttype,
                tuple(comments or ()),
                record_id,
                value,
            )
        )

    def _export_imdinfo(self, model: str, imd_per_id: dict[int, ImdInfo]) -> None:
        records = self._get_records_translatable(imd_per_id.values())
        if not records:
            _debug.logic(
                "translate.export_model_skipped", model=model, xmlids=len(imd_per_id)
            )
            return

        env = records.env
        pushed = len(self._to_translate)  # debuglog
        for record in records.with_context(check_translations=True):
            imd = imd_per_id[record.id]
            module = imd.module
            xml_name = "%s.%s" % (module, imd.name)
            for field_name, field in record._fields.items():
                if (
                    not (field.translate and field.store)
                    or str(field) == "ir.actions.actions.name"
                    or (
                        str(field) == "ir.model.fields.field_description"
                        and not env[record.model]
                        ._fields[record.name]
                        .export_string_translation
                    )
                ):
                    continue
                name = model + "," + field_name
                value_en = record[field_name] or ""
                value_lang = record.with_context(lang=self._lang)[field_name] or ""
                trans_type = "model_terms" if callable(field.translate) else "model"
                try:
                    translation_dictionary = field.get_translation_dictionary(
                        value_en, {self._lang: value_lang}
                    )
                except Exception as exc:
                    _logger.exception(
                        "Failed to extract terms from %s %s", xml_name, name
                    )
                    _debug.logic(
                        "translate.export_terms_failed",
                        xml_id=xml_name,
                        field=name,
                        error=type(exc).__name__,
                    )
                    continue
                for term_en, term_langs in translation_dictionary.items():
                    term_lang = term_langs.get(self._lang)
                    self._push_translation(
                        module,
                        trans_type,
                        name,
                        xml_name,
                        term_en,
                        record_id=imd.res_id,
                        value=term_lang if term_lang != term_en else "",
                    )
        _debug.pipeline(
            "translate.export_model",
            model=model,
            lang=self._lang,
            records=len(records),
            terms=len(self._to_translate) - pushed,
        )

    def _get_records_translatable(self, imd_records: Collection[ImdInfo]) -> Any:
        model = next(iter(imd_records)).model
        if model not in self.env:
            _logger.error("Unable to find object %r", model)
            _debug.logic("translate.export_model_unknown", model=model)
            return self.env["_unknown"].browse()

        if not self.env[model]._translate:
            _debug.logic("translate.export_model_untranslatable", model=model)
            return self.env[model].browse()

        res_ids = [r.res_id for r in imd_records]
        records: Any = self.env[model].browse(res_ids).exists()
        if len(records) < len(res_ids):
            missing_ids = set(res_ids) - set(records.ids)
            missing_records = [
                f"{r.module}.{r.name}" for r in imd_records if r.res_id in missing_ids
            ]
            _logger.warning(
                "Unable to find records of type %r with external ids %s",
                model,
                ", ".join(missing_records),
            )
            _debug.logic(
                "translate.export_records_missing",
                model=model,
                missing=len(missing_ids),
                found=len(records),
            )
            if not records:
                return records

        if model == "ir.model.fields.selection":
            fields: dict[Any, Any] = defaultdict(
                lambda: self.env["ir.model.fields.selection"]
            )
            for selection in records:
                fields[selection.field_id] |= selection
            to_drop: Any = self.env["ir.model.fields.selection"]
            for field, selection in fields.items():
                field_name = field.name
                field_model = self.env.get(field.model)
                if (
                    field_model is None
                    or not field_model._translate
                    or field_name not in field_model._fields
                ):
                    to_drop |= selection
            records -= to_drop
            _debug.logic(
                "translate.export_selections_filtered",
                fields=len(fields),
                dropped=len(to_drop),
                kept=len(records),
            )
        elif model == "ir.model.fields":
            to_drop = self.env["ir.model.fields"]
            for field in records:
                field_name = field.name
                field_model = self.env.get(field.model)
                if (
                    field_model is None
                    or not field_model._translate
                    or field_name not in field_model._fields
                ):
                    to_drop |= field
            records -= to_drop
            _debug.logic(
                "translate.export_fields_filtered",
                dropped=len(to_drop),
                kept=len(records),
            )

        return records


class TranslationRecordReader(TranslationReader):
    def __init__(
        self,
        cr: BaseCursor,
        model_name: str,
        ids: list[int],
        lang: str | None = None,
    ) -> None:
        super().__init__(cr, lang)
        records = self.env[model_name].browse(ids)
        self._export_translatable_records(records, list(records._fields))

    def _export_translatable_records(
        self, records: Any, field_names: list[str]
    ) -> None:
        if not records:
            return

        fields = records._fields

        if records._inherits:
            inherited_fields = defaultdict(list)
            for field_name in field_names:
                field = records._fields[field_name]
                if field.translate and not field.store and field.inherited_field:
                    inherited_fields[field.inherited_field.model_name].append(
                        field_name
                    )
            for parent_mname, parent_fname in records._inherits.items():
                if parent_mname in inherited_fields:
                    self._export_translatable_records(
                        records[parent_fname], inherited_fields[parent_mname]
                    )

        if not any(
            fields[field_name].translate and fields[field_name].store
            for field_name in field_names
        ):
            _debug.logic(
                "translate.export_records_no_translatable_field",
                model=records._name,
                fields=len(field_names),
            )
            return

        with _debug.perf(
            "translate.export_records_xml_ids",
            cr=self._cr,
            model=records._name,
            records=len(records),
        ):
            records._get_or_create_xml_ids()

        model_name = records._name
        query = """SELECT min(concat(module, '.', name)), res_id
                             FROM ir_model_data
                            WHERE model = %s
                              AND res_id = ANY(%s)
                         GROUP BY model, res_id"""

        self._cr.execute(query, (model_name, records.ids))

        imd_per_id = {
            res_id: ImdInfo(
                (tmp := module_xml_name.split(".", 1))[1],
                model_name,
                res_id,
                tmp[0],
            )
            for module_xml_name, res_id in self._cr.fetchall()
        }

        self._export_imdinfo(model_name, imd_per_id)


class TranslationModuleReader(TranslationReader):
    def __init__(
        self, cr: BaseCursor, modules: list[str] | None = None, lang: str | None = None
    ) -> None:
        super().__init__(cr, lang)
        self._modules = modules or ["all"]
        self._path_list = [(path, True, True) for path in odoo.addons.__path__]
        self._installed_modules = [
            m["name"]
            for m in self.env["ir.module.module"].search_read(
                [("state", "=", "installed")], fields=["name"]
            )
        ]

        self._export_translatable_records()
        self._export_translatable_resources()

    def _selected_modules(self) -> list[str]:
        if "all" in self._modules:
            return list(self._installed_modules)
        return list(self._modules)

    def _export_translatable_records(self) -> None:
        modules = self._selected_modules()
        xml_defined: set[tuple] = set()
        with _debug.perf(
            "translate.export_datafile_scan", cr=self._cr, modules=len(modules)
        ):
            for module in modules:
                for filepath in get_datafile_translation_path(module):
                    fileformat = Path(filepath).suffix[1:].lower()
                    with file_open(filepath, mode="rb") as source:
                        xml_defined.update(
                            (entry["imd_model"], module, entry["imd_name"])
                            for entry in translation_file_reader(
                                source, fileformat=fileformat, module=module
                            )
                        )

        query = """SELECT min(name), model, res_id, module
                     FROM ir_model_data
                    WHERE module = ANY(%s)
                 GROUP BY model, res_id, module
                 ORDER BY module, model, min(name)"""

        self._cr.execute(query, (modules,))

        records_per_model: defaultdict[str, dict] = defaultdict(dict)
        skipped = 0  # debuglog
        for imd_name, model, res_id, module in self._cr.fetchall():
            if (model, module, imd_name) in xml_defined:
                skipped += 1  # debuglog
                continue
            records_per_model[model][res_id] = ImdInfo(imd_name, model, res_id, module)
        _debug.pipeline(
            "translate.export_records_planned",
            lang=self._lang,
            modules=len(modules),
            models=len(records_per_model),
            xml_defined=len(xml_defined),
            skipped=skipped,
        )

        with _debug.perf(
            "translate.export_records_all",
            cr=self._cr,
            lang=self._lang,
            models=len(records_per_model),
        ):
            for model, imd_per_id in records_per_model.items():
                self._export_imdinfo(model, imd_per_id)

    def _get_module_from_path(self, path: str) -> str:
        p = Path(path)
        for mp, _recursive, is_addons_root in self._path_list:
            mp_path = Path(mp)
            try:
                rel = p.relative_to(mp_path)
            except ValueError:
                continue
            if is_addons_root and str(p.parent) != str(mp_path):
                return rel.parts[0]
        return "base"

    def _verified_module_filepaths(
        self, fname: str, path: str, root: str
    ) -> tuple[str, str, str, str] | None:
        fabsolutepath = str(Path(root, fname))
        frelativepath = fabsolutepath.removeprefix(path)
        display_path = f"addons{frelativepath}"
        module = self._get_module_from_path(fabsolutepath)
        if (
            module
            and ("all" in self._modules or module in self._modules)
            and module in self._installed_modules
        ):
            display_path = display_path.replace(os.sep, "/")
            return module, fabsolutepath, frelativepath, display_path
        return None

    def _babel_extract_terms(
        self,
        fname: str,
        path: str,
        root: str,
        extract_method: str = "odoo.tools.babel_extractors:extract_python",
        trans_type: str = "code",
        extra_comments: list[str] | None = None,
        extract_keywords: dict | None = None,
    ) -> None:
        if extract_keywords is None:
            extract_keywords = {"_": None}
        verified = self._verified_module_filepaths(fname, path, root)
        if verified is None:
            return
        module, fabsolutepath, _, display_path = verified
        extra_comments = extra_comments or []
        src_file: IO[bytes] | None = None
        options = {}
        if "python" in extract_method:
            options["encoding"] = "UTF-8"
            translations = code_translations.get_python_translations(module, self._lang)
        else:
            web_translations = code_translations.get_web_translations(
                module, self._lang
            )
            translations = {
                tran["id"]: tran["string"] for tran in web_translations["messages"]
            }
        extracted_count = 0  # debuglog
        try:
            src_file = file_open(fabsolutepath, "rb")
            for extracted in extract.extract(
                extract_method,
                src_file,
                keywords=extract_keywords,
                options=options,
            ):
                lineno, message, comments = extracted[:3]
                value = translations.get(message, "")
                extracted_count += 1  # debuglog
                self._push_translation(
                    module,
                    trans_type,
                    display_path,
                    lineno,
                    message,
                    comments + extra_comments,
                    value=value,
                )
        except Exception as exc:
            _logger.exception("Failed to extract terms from %s", fabsolutepath)
            _debug.logic(
                "translate.extract_failed",
                module=module,
                file=display_path,
                method=extract_method.rpartition(":")[2],
                error=type(exc).__name__,
            )
        finally:
            if src_file is not None:
                src_file.close()
        _debug.perf.count(
            "translate.extract_file",
            module=module,
            file=display_path,
            method=extract_method.rpartition(":")[2],
            terms=extracted_count,
        )

    def _walk_starts(self) -> Iterator[tuple[str, str, bool]]:
        wanted = None if "all" in self._modules else set(self._modules)
        for path, recursive, is_addons_root in self._path_list:
            if wanted is None:
                yield path, path, recursive
            elif not is_addons_root:
                if "base" in wanted:
                    yield path, path, recursive
            else:
                try:
                    with os.scandir(path) as entries:
                        starts = [
                            entry.path
                            for entry in entries
                            if entry.name in wanted and entry.is_dir()
                        ]
                except OSError:
                    _debug.logic("translate.walk_root_unreadable", path=path)
                    continue
                _debug.logic(
                    "translate.walk_narrowed",
                    path=path,
                    wanted=len(wanted),
                    found=len(starts),
                )
                for start in starts:
                    yield start, path, recursive

    def _export_translatable_resources(self) -> None:

        for bin_path in ["orm", "modules", "service", "tools"]:
            self._path_list.append((str(Path(config.root_path, bin_path)), True, False))
        self._path_list.append((config.root_path, False, False))
        _logger.debug("Scanning modules at paths: %s", self._path_list)

        spreadsheet_files_regex = re.compile(r".*_dashboard(\.osheet)?\.json$")

        _debug.pipeline(
            "translate.export_resources",
            lang=self._lang,
            modules=self._modules,
            paths=len(self._path_list),
            installed=len(self._installed_modules),
        )
        for start, path, recursive in self._walk_starts():
            _logger.debug("Scanning files of modules at %s", start)
            for root, _dummy, files in os.walk(start, followlinks=True):
                for fname in fnmatch.filter(files, "*.py"):
                    self._babel_extract_terms(
                        fname,
                        path,
                        root,
                        "odoo.tools.babel_extractors:extract_python",
                        extra_comments=[PYTHON_TRANSLATION_COMMENT],
                        extract_keywords={"_": None, "_lt": None},
                    )
                if fnmatch.fnmatch(root, "*/static/src*"):
                    for fname in fnmatch.filter(files, "*.js"):
                        self._babel_extract_terms(
                            fname,
                            path,
                            root,
                            "odoo.tools.babel_extractors:extract_javascript",
                            extra_comments=[JAVASCRIPT_TRANSLATION_COMMENT],
                            extract_keywords={"_t": None},
                        )
                    for fname in fnmatch.filter(files, "*.xml"):
                        self._babel_extract_terms(
                            fname,
                            path,
                            root,
                            "odoo.tools.translate:babel_extract_qweb",
                            extra_comments=[JAVASCRIPT_TRANSLATION_COMMENT],
                        )
                if fnmatch.fnmatch(root, "*/data/*"):
                    for fname in filter(spreadsheet_files_regex.match, files):
                        self._babel_extract_terms(
                            fname,
                            path,
                            root,
                            "odoo.tools.translate:extract_spreadsheet_terms",
                            extra_comments=[JAVASCRIPT_TRANSLATION_COMMENT],
                        )
                if not recursive:
                    break

        self._export_attachment_translations()

    def _export_attachment_translations(self) -> None:
        IrModuleModule = self.env["ir.module.module"]
        modules = self._selected_modules()
        before = len(self._to_translate)  # debuglog
        for module in modules:
            for translation in IrModuleModule._extract_resource_attachment_translations(
                module, self._lang
            ):
                self._push_translation(*translation)
        _debug.perf.count(
            "translate.export_attachment_terms",
            lang=self._lang,
            modules=len(modules),
            terms=len(self._to_translate) - before,
        )


def DeepDefaultDict() -> defaultdict:
    return defaultdict(DeepDefaultDict)


class TranslationImporter:
    def __init__(self, cr: BaseCursor, verbose: bool = True) -> None:
        self.cr = cr
        self.verbose = verbose
        from odoo import api

        self.env = api.Environment(cr, api.SUPERUSER_ID, {})

        self.model_translations = DeepDefaultDict()
        self.model_terms_translations = DeepDefaultDict()
        self.imported_langs: set[str] = set()

    def load_file(
        self,
        filepath: str,
        lang: str,
        xmlids: Collection[str] | None = None,
        module: str | None = None,
    ) -> None:
        with (
            suppress(FileNotFoundError),
            file_open(filepath, mode="rb") as fileobj,
        ):
            if self.verbose:
                _logger.info(
                    "loading base translation file %s for language %s",
                    filepath,
                    lang,
                )
            fileformat = Path(filepath).suffix[1:].lower()
            self.load(fileobj, fileformat, lang, xmlids=xmlids, module=module)

    def load(
        self,
        fileobj: IO[bytes],
        fileformat: str,
        lang: str,
        xmlids: Collection[str] | None = None,
        module: str | None = None,
    ) -> None:
        if self.verbose:
            _logger.info("loading translation file for language %s", lang)
        if not self.env["res.lang"]._get_lang_cached(lang):
            _logger.error(
                "Couldn't read translation for lang '%s', language not found",
                lang,
            )
            _debug.logic("translate.load_lang_missing", lang=lang, module=module)
            return
        try:
            fileobj.seek(0)
            reader = translation_file_reader(
                fileobj, fileformat=fileformat, module=module
            )
            with _debug.perf(
                "translate.load_file",
                lang=lang,
                format=fileformat,
                module=module,
                file=getattr(fileobj, "name", None),
            ):
                self._load(reader, lang, xmlids)
        except OSError as exc:
            _logger.exception(
                "couldn't read translation file %s [lang: %s][format: %s]",
                getattr(fileobj, "name", "<stream>"),
                get_iso_codes(lang),
                fileformat,
            )
            _debug.logic(
                "translate.load_file_unreadable",
                lang=lang,
                format=fileformat,
                module=module,
                error=type(exc).__name__,
            )

    def _load(
        self,
        reader: Iterable[dict],
        lang: str,
        xmlids: Collection[str] | None = None,
    ) -> None:
        # a set, even empty, is a filter: nothing outside it is loaded
        wanted = None if xmlids is None else set(xmlids)
        valid_langs = get_base_langs(lang)
        rows = sorted(
            reader,
            key=lambda r: (
                valid_langs.index(r.get("lang", lang))
                if r.get("lang", lang) in valid_langs
                else -1
            ),
        )
        model = model_terms = 0  # debuglog
        skipped: dict[str, int] = defaultdict(int)  # debuglog
        for row in rows:
            if not row.get("value") or not row.get("src"):
                skipped["empty"] += 1  # debuglog
                continue
            if row.get("type") == "code":
                skipped["code"] += 1  # debuglog
                continue
            if row.get("lang", lang) not in valid_langs:
                skipped["lang"] += 1  # debuglog
                continue
            model_name = row.get("imd_model")
            module_name = row["module"]
            if not model_name or model_name not in self.env:
                skipped["model"] += 1  # debuglog
                continue
            field_name = row["name"].split(",")[1]
            field = self.env[model_name]._fields.get(field_name)
            if not field or not field.translate or not field.store:
                skipped["field"] += 1  # debuglog
                continue
            xmlid = module_name + "." + row["imd_name"]
            if wanted is not None and xmlid not in wanted:
                skipped["xmlid"] += 1  # debuglog
                continue
            if row.get("type") == "model" and field.translate is True:
                self.model_translations[model_name][field_name][xmlid][lang] = row[
                    "value"
                ]
                self.imported_langs.add(lang)
                model += 1  # debuglog
            elif row.get("type") == "model_terms" and callable(field.translate):
                self.model_terms_translations[model_name][field_name][xmlid][
                    row["src"]
                ][lang] = row["value"]
                self.imported_langs.add(lang)
                model_terms += 1  # debuglog
            else:
                skipped["type_mismatch"] += 1  # debuglog
        kept = model + model_terms  # debuglog
        _debug.pipeline(
            "translate.load_rows",
            lang=lang,
            valid_langs=valid_langs,
            rows=len(rows),
            kept=kept,
            model=model,
            model_terms=model_terms,
            skipped=dict(skipped),
        )

    def _get_terms_rows(
        self,
        model_table: str,
        model_name: str,
        field_name: str,
        sub_xmlids: tuple[str, ...],
        field_dictionary: dict,
    ) -> dict[int, list]:
        self.cr.execute(
            SQL(
                """
                SELECT m.id, imd.module || '.' || imd.name, %(field)s, imd.noupdate
                FROM %(table)s m, "ir_model_data" imd
                WHERE m.id = imd.res_id AND imd.model = %(model)s AND (%(match)s)
                """,
                field=SQL.identifier("m", field_name),
                table=SQL.identifier(model_table),
                model=model_name,
                match=SQL(" OR ").join(
                    SQL(
                        "(imd.module = %s AND imd.name = %s)",
                        *xmlid.split(".", maxsplit=1),
                    )
                    for xmlid in sub_xmlids
                ),
            )
        )

        rows_by_id: dict[int, list] = {}
        for id_, xmlid, values, noupdate in self.cr.fetchall():
            if not values:
                continue
            entry = rows_by_id.get(id_)
            if entry is None:
                entry = rows_by_id[id_] = [values, noupdate, {}]
            merged = entry[2]
            for src, translations in field_dictionary[xmlid].items():
                merged.setdefault(src, {}).update(translations)
        return rows_by_id

    @staticmethod
    def _merge_translation_dictionary(
        field: BaseString,
        values: dict,
        record_dictionary: dict,
        noupdate: bool,
        overwrite: bool,
        force_overwrite: bool,
    ) -> tuple[dict, set[str]]:
        _value_en = values.get("_en_US", values["en_US"])
        langs = {
            lang for translations in record_dictionary.values() for lang in translations
        }
        translation_dictionary = field.get_translation_dictionary(
            _value_en,
            {k: values.get(f"_{k}", v) for k, v in values.items() if k in langs},
        )

        if force_overwrite or (not noupdate and overwrite):
            for term_en, translations in record_dictionary.items():
                translation_dictionary[term_en].update(translations)
        else:
            for term_en, translations in record_dictionary.items():
                translations.update(
                    {
                        k: v
                        for k, v in translation_dictionary[term_en].items()
                        if v != term_en
                    }
                )
                translation_dictionary[term_en] = translations
        return translation_dictionary, langs

    @staticmethod
    def _changed_translation_values(
        translate: TranslateDialect,
        value_en: str,
        values: dict,
        langs: set[str],
        translation_dictionary: dict,
    ) -> dict:
        changed_values = {}
        for lang in langs:
            terms = {
                term: translations[lang]
                for term, translations in translation_dictionary.items()
                if lang in translations
            }
            new_val = translate(terms.get, value_en)
            if values.get(lang) != new_val:
                changed_values[lang] = new_val
            if f"_{lang}" in values:
                changed_values[f"_{lang}"] = None
        return changed_values

    def _write_terms_batch(
        self, model_table: str, field_name: str, rows: list[tuple[int, Json]]
    ) -> None:
        column = SQL.identifier(field_name)
        self.env.cr.execute(
            SQL(
                """
                UPDATE %(table)s AS m
                SET %(column)s = jsonb_strip_nulls(m.%(column)s || t.value)
                FROM (VALUES %(rows)s) AS t(id, value)
                WHERE m.id = t.id
                """,
                table=SQL.identifier(model_table),
                column=column,
                rows=SQL(", ").join(
                    SQL("(%s, %s::jsonb)", id_, value) for id_, value in rows
                ),
            )
        )

    def _save_model_terms_translations(
        self, overwrite: bool, force_overwrite: bool
    ) -> None:
        env = self.env
        for model_name, model_dictionary in self.model_terms_translations.items():
            Model = env[model_name]
            model_table = Model._table
            fields = Model._fields
            for field_name, field_dictionary in model_dictionary.items():
                field = fields.get(field_name)
                for sub_xmlids in batched(
                    field_dictionary.keys(), self.cr.BATCH_SIZE, strict=False
                ):
                    rows_by_id = self._get_terms_rows(
                        model_table,
                        model_name,
                        field_name,
                        sub_xmlids,
                        field_dictionary,
                    )
                    rows: list[tuple[int, Json]] = []
                    for id_, (
                        values,
                        noupdate,
                        record_dictionary,
                    ) in rows_by_id.items():
                        _value_en = values.get("_en_US", values["en_US"])
                        if not _value_en:
                            continue
                        translation_dictionary, langs = (
                            self._merge_translation_dictionary(
                                field,
                                values,
                                record_dictionary,
                                noupdate,
                                overwrite,
                                force_overwrite,
                            )
                        )
                        changed_values = self._changed_translation_values(
                            field.translate,
                            _value_en,
                            values,
                            langs,
                            translation_dictionary,
                        )
                        if changed_values:
                            rows.append((id_, Json(changed_values)))
                    _debug.perf.count(
                        "translate.save_terms_batch",
                        model=model_name,
                        field=field_name,
                        xmlids=len(sub_xmlids),
                        records=len(rows_by_id),
                        changed=len(rows),
                    )
                    if rows:
                        self._write_terms_batch(model_table, field_name, rows)

        self.model_terms_translations.clear()

    def _save_model_translations(self, overwrite: bool, force_overwrite: bool) -> None:
        env = self.env
        for model_name, model_dictionary in self.model_translations.items():
            model_table = env[model_name]._table
            for field_name, field_dictionary in model_dictionary.items():
                column = SQL.identifier(field_name)
                if force_overwrite:
                    value_query = SQL("m.%(column)s || t.value", column=column)
                else:
                    value_query = SQL(
                        """CASE WHEN %(overwrite)s IS TRUE AND imd.noupdate IS NOT TRUE
                        THEN m.%(column)s || t.value
                        ELSE t.value || m.%(column)s END""",
                        overwrite=overwrite,
                        column=column,
                    )
                for sub_field_dictionary in batched(
                    field_dictionary.items(), self.cr.BATCH_SIZE, strict=False
                ):
                    _debug.perf.count(
                        "translate.save_model_batch",
                        model=model_name,
                        field=field_name,
                        xmlids=len(sub_field_dictionary),
                        overwrite=overwrite,
                        force=force_overwrite,
                    )
                    env.cr.execute(
                        SQL(
                            """
                            UPDATE %(table)s AS m
                            SET %(column)s = %(value)s
                            FROM (VALUES %(rows)s)
                                AS t(imd_module, imd_name, value)
                            JOIN "ir_model_data" AS imd
                            ON imd."model" = %(model)s
                            AND imd.name = t.imd_name
                            AND imd.module = t.imd_module
                            WHERE imd."res_id" = m."id"
                            """,
                            table=SQL.identifier(model_table),
                            column=column,
                            value=value_query,
                            rows=SQL(", ").join(
                                SQL(
                                    "(%s, %s, %s::jsonb)",
                                    *xmlid.split(".", maxsplit=1),
                                    Json(translations),
                                )
                                for xmlid, translations in sub_field_dictionary
                            ),
                            model=model_name,
                        )
                    )

        self.model_translations.clear()

    def save(self, overwrite: bool = False, force_overwrite: bool = False) -> None:
        if not self.model_translations and not self.model_terms_translations:
            _debug.logic("translate.save_nothing", langs=sorted(self.imported_langs))
            return

        env = self.env
        env.flush_all()

        with _debug.perf(
            "translate.save",
            cr=self.cr,
            langs=sorted(self.imported_langs),
            models=len(self.model_translations),
            terms_models=len(self.model_terms_translations),
            overwrite=overwrite,
            force=force_overwrite,
        ):
            self._save_model_terms_translations(overwrite, force_overwrite)
            self._save_model_translations(overwrite, force_overwrite)

        env.invalidate_all()
        env.registry.clear_cache()
        _debug.lifecycle("translate.saved", langs=sorted(self.imported_langs))
        if self.verbose:
            _logger.info("translations are loaded successfully")


def get_locales(lang: str) -> Iterator[str]:
    encodings = ["utf8"]
    if prefenc := locale.getpreferredencoding():
        encodings.append(prefenc)
        if aliased := {
            "latin1": "latin9",
            "iso-8859-1": "iso8859-15",
            "cp1252": "1252",
        }.get(prefenc.lower()):
            encodings.append(aliased)

    seen = set()
    for enc in encodings:
        ln = locale._build_localename((lang, enc))  # type: ignore[attr-defined]
        for name in (ln, locale.normalize(ln)):
            if name not in seen:
                seen.add(name)
                yield name
    if lang not in seen:
        yield lang


def resetlocale() -> str:
    try:
        return locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        _debug.logic("translate.locale_env_unusable")
        return locale.setlocale(locale.LC_ALL, "C")


def load_language(cr: BaseCursor, lang: str) -> None:
    from odoo import api

    env = api.Environment(cr, api.SUPERUSER_ID, {})
    lang_ids = (
        env["res.lang"]
        .with_context(active_test=False)
        .search([("code", "=", lang)])
        .ids
    )
    installer: Any = env["base.language.install"].create(
        {"lang_ids": [(6, 0, lang_ids)]}
    )
    with _debug.perf("translate.load_language", cr=cr, lang=lang, langs=lang_ids):
        installer.action_install_lang()


def get_base_langs(lang: str) -> list[str]:
    base_lang = lang.split("_", 1)[0]
    langs = [base_lang]
    if base_lang == "es" and lang not in ("es_ES", "es_419"):
        langs.append("es_419")
    if lang == "zh_HK":
        langs.append("zh_TW")
    if lang != base_lang:
        langs.append(lang)
    return langs


def get_po_paths(module_name: str, lang: str) -> Iterator[str]:
    po_paths = (
        str(Path(module_name, dir_, filename + ".po"))
        for filename in get_base_langs(lang)
        for dir_ in ("i18n", "i18n_extra")
    )
    for path in po_paths:
        with suppress(FileNotFoundError):
            yield file_path(path)


def get_datafile_translation_path(module_name: str) -> Iterator[str]:
    from odoo.modules import Manifest

    manifest: Any = Manifest.for_addon(module_name, display_warning=False) or {}
    for data_type in ("data", "demo"):
        for path in manifest.get(data_type, ()):
            if path.endswith((".xml", ".csv")):
                yield file_path(str(Path(module_name, path)))


class CodeTranslations:
    def __init__(self) -> None:
        self.python_translations: dict[tuple[str, str], Mapping] = {}
        self.web_translations: dict[tuple[str, str], Mapping] = {}

    @staticmethod
    def _read_code_translations_file(
        fileobj: IO[bytes], filter_func: Callable[[dict], bool]
    ) -> dict[str, str]:
        translations = {}
        fileobj.seek(0)
        reader = translation_file_reader(fileobj, fileformat="po")
        for row in reader:
            if row.get("type") == "code" and row.get("src") and filter_func(row):
                translations[row["src"]] = row["value"]
        return translations

    @staticmethod
    def _get_code_translations(
        module_name: str, lang: str, filter_func: Callable[[dict], bool]
    ) -> dict[str, str]:
        po_paths = get_po_paths(module_name, lang)
        translations = {}
        files = 0  # debuglog
        for po_path in po_paths:
            try:
                with file_open(po_path, mode="rb") as fileobj:
                    p = CodeTranslations._read_code_translations_file(
                        fileobj, filter_func
                    )
                translations.update(p)
                files += 1  # debuglog
            except OSError:
                _logger.exception(
                    "couldn't read translation file %s [lang: %s]",
                    po_path,
                    get_iso_codes(lang),
                )
        _debug.perf.count(
            "translate.code_translations_loaded",
            module=module_name,
            lang=lang,
            files=files,
            terms=len(translations),
        )
        return translations

    @staticmethod
    def _load_python_translations(module_name: str, lang: str) -> Mapping[str, str]:
        def filter_func(row: dict) -> bool:
            return (
                bool(row.get("value")) and PYTHON_TRANSLATION_COMMENT in row["comments"]
            )

        translations = CodeTranslations._get_code_translations(
            module_name, lang, filter_func
        )
        return ReadonlyDict(translations)

    @staticmethod
    def _load_web_translations(module_name: str, lang: str) -> Mapping:
        def filter_func(row: dict) -> bool:
            return (
                bool(row.get("value"))
                and JAVASCRIPT_TRANSLATION_COMMENT in row["comments"]
            )

        translations = CodeTranslations._get_code_translations(
            module_name, lang, filter_func
        )
        return ReadonlyDict(
            {
                "messages": tuple(
                    ReadonlyDict({"id": src, "string": value})
                    for src, value in translations.items()
                )
            }
        )

    def clear(self, module_name: str | None = None) -> None:
        _debug.lifecycle(
            "translate.code_translations_cleared",
            module=module_name,
            python=len(self.python_translations),
            web=len(self.web_translations),
        )
        if module_name is None:
            self.python_translations.clear()
            self.web_translations.clear()
            return
        for cache in (self.python_translations, self.web_translations):
            # list() snapshots the keys in one step: request threads insert
            # while a registry reload clears
            for key in [k for k in list(cache) if k[0] == module_name]:
                cache.pop(key, None)

    def get_python_translations(self, module_name: str, lang: str) -> Mapping[str, str]:
        key = (module_name, lang)
        try:
            return self.python_translations[key]
        except KeyError:
            translations = self._load_python_translations(module_name, lang)
            self.python_translations[key] = translations
            return translations

    def get_web_translations(self, module_name: str, lang: str) -> Mapping:
        key = (module_name, lang)
        try:
            return self.web_translations[key]
        except KeyError:
            translations = self._load_web_translations(module_name, lang)
            self.web_translations[key] = translations
            return translations


code_translations = CodeTranslations()
