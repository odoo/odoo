import html as htmllib
import itertools
import logging
import re
from typing import TYPE_CHECKING, Any, Literal, overload
from urllib.parse import urlparse

import markupsafe
from lxml import etree, html
from lxml.html import (
    XHTML_NAMESPACE,
    _contains_block_level_tag,
    _looks_like_full_html_bytes,
    _looks_like_full_html_unicode,
    clean,
    defs,
    document_fromstring,
    html_parser,
)
from markupsafe import Markup, escape_silent

from odoo.libs.web.urls import urljoin

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "HTML_NEWLINES_REGEX",
    "HTML_TAGS_REGEX",
    "HTML_TAG_URL_REGEX",
    "SANITIZE_TAGS",
    "TEXT_URL_REGEX",
    "URL_REGEX",
    "URL_SKIP_PROTOCOL_REGEX",
    "VOID_ELEMENTS",
    "add_html_content",
    "create_link",
    "fromstring",
    "html2plaintext",
    "html_escape",
    "html_keep_url",
    "html_normalize",
    "html_sanitize",
    "html_to_inner_content",
    "is_html_empty",
    "nl2br",
    "nl2br_enclose",
    "normalize_url",
    "plaintext2html",
    "prepend_html_content",
    "replace_local_links",
    "safe_attrs",
    "tag_quote",
]


VOID_ELEMENTS = frozenset(
    [
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "keygen",
        "link",
        "menuitem",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    ]
)

html_escape = markupsafe.escape


def nl2br(string: str) -> Markup:
    return escape_silent(string).replace("\n", Markup("<br>\n"))


def nl2br_enclose(string: str, enclosure_tag: str = "div") -> Markup:
    return Markup("<{enclosure_tag}>{converted}</{enclosure_tag}>").format(
        enclosure_tag=enclosure_tag,
        converted=nl2br(string),
    )


safe_attrs = defs.safe_attrs | frozenset(
    [
        "style",
        "data-o-mail-quote",
        "data-o-mail-quote-node",
        "data-o-mail-quote-container",
        "data-oe-model",
        "data-oe-id",
        "data-oe-field",
        "data-oe-type",
        "data-oe-expression",
        "data-oe-translation-source-sha",
        "data-oe-nodeid",
        "data-last-history-steps",
        "data-oe-protected",
        "data-embedded",
        "data-embedded-editable",
        "data-embedded-props",
        "data-oe-version",
        "data-oe-transient-content",
        "data-behavior-props",
        "data-prop-name",
        "data-width",
        "data-height",
        "data-scale-x",
        "data-scale-y",
        "data-x",
        "data-y",
        "data-oe-role",
        "data-oe-aria-label",
        "data-publish",
        "data-id",
        "data-res_id",
        "data-interval",
        "data-member_id",
        "data-scroll-background-ratio",
        "data-view-id",
        "data-class",
        "data-mimetype",
        "data-original-src",
        "data-original-id",
        "data-gl-filter",
        "data-quality",
        "data-resize-width",
        "data-shape",
        "data-shape-colors",
        "data-file-name",
        "data-original-mimetype",
        "data-attachment-id",
        "data-format-mimetype",
        "data-ai-field",
        "data-ai-record-id",
        "data-heading-link-id",
        "data-mimetype-before-conversion",
        "data-language-id",
        "data-bs-toggle",
    ]
)

SANITIZE_TAGS = {
    "allow_tags": defs.tags
    | frozenset(
        [
            "article",
            "bdi",
            "section",
            "header",
            "footer",
            "hgroup",
            "nav",
            "aside",
            "figure",
            "main",
        ]
        + [etree.Comment]
    ),
    "kill_tags": [
        "base",
        "embed",
        "frame",
        "head",
        "iframe",
        "link",
        "meta",
        "noscript",
        "object",
        "script",
        "style",
        "title",
    ],
    "remove_tags": ["html", "body"],
}


class _Cleaner(clean.Cleaner):
    _style_re = re.compile(r"""([\w-]+)\s*:\s*((?:[^;"']|"[^";]*"|'[^';]*')+)""")

    _style_whitelist_base = (
        "font-size",
        "font-family",
        "font-weight",
        "font-style",
        "background-color",
        "color",
        "text-align",
        "line-height",
        "letter-spacing",
        "text-transform",
        "text-decoration",
        "opacity",
        "float",
        "vertical-align",
        "display",
        "object-fit",
        "padding",
        "padding-top",
        "padding-left",
        "padding-bottom",
        "padding-right",
        "margin",
        "margin-top",
        "margin-left",
        "margin-bottom",
        "margin-right",
        "white-space",
        "background-image",
        "background-position",
        "background-size",
        "background-repeat",
        "background-origin",
        "border",
        "border-color",
        "border-radius",
        "border-style",
        "border-width",
        "border-top",
        "border-bottom",
        "height",
        "width",
        "max-width",
        "min-width",
        "min-height",
        "border-collapse",
        "border-spacing",
        "caption-side",
        "empty-cells",
        "table-layout",
    )

    _style_whitelist = frozenset(_style_whitelist_base) | {
        f"border-{position}-{attribute}"
        for position in ["top", "bottom", "left", "right"]
        for attribute in (
            "style",
            "color",
            "width",
            "left-radius",
            "right-radius",
        )
    }

    strip_classes = False
    sanitize_style = False
    conditional_comments = True

    _XML_BASE_ATTRS = ("xml:base", "{http://www.w3.org/XML/1998/namespace}base")

    def __call__(self, doc: etree._Element) -> None:
        super().__call__(doc)

        for el in doc.iter(tag=etree.Element):
            for attr in self._XML_BASE_ATTRS:
                el.attrib.pop(attr, None)

        if not getattr(self, "safe_attrs_only", False) and self.strip_classes:
            for el in doc.iter(tag=etree.Element):
                self.strip_class(el)

        if not self.style and self.sanitize_style:
            for el in doc.iter(tag=etree.Element):
                self.parse_style(el)

    def strip_class(self, el: etree._Element) -> None:
        if el.attrib.get("class"):
            del el.attrib["class"]

    def parse_style(self, el: etree._Element) -> None:
        attributes = el.attrib
        styling = attributes.get("style")
        if styling:
            valid_styles = {}
            styles = self._style_re.findall(styling)
            for style in styles:
                if style[0].lower() in self._style_whitelist:
                    valid_styles[style[0].lower()] = style[1]
            if valid_styles:
                el.attrib["style"] = "; ".join(
                    f"{key}:{val}" for (key, val) in valid_styles.items()
                )
            else:
                del el.attrib["style"]

    def kill_conditional_comments(self, doc: etree._Element) -> None:
        if self.conditional_comments:
            super().kill_conditional_comments(doc)


_QUOTE = "data-o-mail-quote"
_QUOTE_CONTAINER = "data-o-mail-quote-container"
_QUOTE_NODE = "data-o-mail-quote-node"


def _wrap_matches_in_text(
    regex: re.Pattern[str],
    node: etree._Element,
    tag: str = "span",
    attrs: dict[str, str] | None = None,
) -> None:
    text = node.text or ""
    matches = list(regex.finditer(text))
    if not matches:
        return

    previous: etree._Element | None = None
    idx = 0
    for position, match in enumerate(matches):
        wrapper = etree.Element(tag)
        wrapper.text = text[match.start() : match.end()]
        wrapper.tail = text[match.end() :]
        for key, val in (attrs or {}).items():
            wrapper.set(key, val)
        if previous is None:
            node.text = text[idx : match.start()]
        else:
            previous.tail = text[idx : match.start()]
        node.insert(position, wrapper)
        previous = wrapper
        idx = match.end()


def _mark_quote(el: etree._Element, *, container_on_parent: bool = False) -> None:
    el.set(_QUOTE, "1")
    if container_on_parent and (parent := el.getparent()) is not None:
        parent.set(_QUOTE_CONTAINER, "1")


def _quote_client_markers(el: etree._Element, el_class: str, el_id: str) -> None:
    if "gmail_extra" in el_class or "SkyDrivePlaceholder" in el_class:
        _mark_quote(el, container_on_parent=True)

    if (
        el.tag == "hr" and ("stopSpelling" in el_class or "stopSpelling" in el_id)
    ) or "yahoo_quoted" in el_class:
        el.set(_QUOTE, "1")
        for sibling in el.itersiblings(preceding=False):
            sibling.set(_QUOTE, "1")

    is_signature_wrapper = (
        "odoo_signature_wrapper" in el_class
        or "gmail_signature" in el_class
        or el_id == "Signature"
    )
    is_outlook_reply_quote = "divRplyFwdMsg" in el_id
    if is_signature_wrapper or "gmail_quote" in el_class or is_outlook_reply_quote:
        el.set(_QUOTE_CONTAINER, "1")
        el.set(_QUOTE, "1")

    if is_outlook_reply_quote:
        hr = el.getprevious()
        if hr is not None and hr.tag == "hr":
            hr.set(_QUOTE, "1")
        if (reply_quote := el.getnext()) is not None:
            reply_quote.set(_QUOTE_CONTAINER, "1")
            reply_quote.set(_QUOTE, "1")

    if "appendonsend" in el_id and not (el.text or "").strip():
        el.set(_QUOTE_CONTAINER, "1")
        el.set(_QUOTE, "1")


def _quote_inherited_from_parent(el: etree._Element) -> None:
    parent = el.getparent()
    if parent is None or parent.get(_QUOTE_NODE):
        return
    if parent.get(_QUOTE):
        el.set(_QUOTE, "1")
        return
    if not parent.get(_QUOTE_CONTAINER):
        return
    first_sibling_quote = parent.find(f"*[@{_QUOTE}]")
    if first_sibling_quote is None:
        return
    siblings = list(parent)
    if siblings.index(first_sibling_quote) < siblings.index(el):
        el.set(_QUOTE, "1")


def tag_quote(el: etree._Element) -> None:
    el_class = el.get("class", "") or ""
    el_id = el.get("id", "") or ""

    _quote_client_markers(el, el_class, el_id)

    if el.text and el.find("br") is not None and _SIGNATURE_BEGIN_RE.search(el.text):
        _mark_quote(el, container_on_parent=True)

    if not el.get(_QUOTE):
        _wrap_matches_in_text(_TEXT_COMPLETE_RE, el, "span", {_QUOTE: "1"})

    if el.tag == "blockquote":
        el.set(_QUOTE_NODE, "1")
        el.set(_QUOTE, "1")

    _quote_inherited_from_parent(el)

    previous = el.getprevious()
    if previous is not None and previous.get(_QUOTE) and not el.text_content().strip():
        el.set(_QUOTE, "1")


def _get_elements_by_tag(doc: etree._Element, tag: str) -> list[etree._Element]:
    return doc.findall(tag) or doc.findall(f"{{{XHTML_NAMESPACE}}}{tag}")


def _merge_into_first(elements: list[etree._Element]) -> etree._Element:
    survivor = elements[0]
    for other in elements[1:]:
        if other.text:
            if len(survivor):
                survivor[-1].tail = (survivor[-1].tail or "") + other.text
            else:
                survivor.text = (survivor.text or "") + other.text
        survivor.extend(other)
        other.drop_tree()
    return survivor


def _wrap_loose_body_text(body: etree._Element) -> None:
    if not (body.text and body.text.strip()):
        return

    paragraph = body.makeelement("p", {})
    paragraph.text = body.text
    body.text = None

    if len(body) == 0:
        body.append(paragraph)
    elif _contains_block_level_tag(body):
        while len(body) and body[0].tag not in defs.block_tags:
            paragraph.append(body[0])
        body.insert(0, paragraph)
    else:
        for child in list(body):
            paragraph.append(child)
        body.append(paragraph)


def fromstring(
    html_: str | bytes,
    base_url: str | None = None,
    parser: Any = None,
    **kw: Any,
) -> tuple[etree._Element, bool]:
    if parser is None:
        parser = html_parser
    looks_full_html = (
        _looks_like_full_html_bytes
        if isinstance(html_, bytes)
        else _looks_like_full_html_unicode
    )
    is_full_html = looks_full_html(html_)
    doc = document_fromstring(html_, parser=parser, base_url=base_url, **kw)
    if is_full_html:
        return doc, False

    bodies = _get_elements_by_tag(doc, "body")
    body = _merge_into_first(bodies) if bodies else None

    if heads := _get_elements_by_tag(doc, "head"):
        _merge_into_first(heads)
        return doc, False
    if body is None:
        return doc, False

    _wrap_loose_body_text(body)

    if (
        len(body) == 1
        and (not body.text or not body.text.strip())
        and (not body[-1].tail or not body[-1].tail.strip())
    ):
        return body[0], True
    body.tag = "div" if _contains_block_level_tag(body) else "span"
    return body, False


def html_normalize(
    src: str,
    filter_callback: Callable[[etree._Element], etree._Element] | None = None,
    output_method: str = "html",
) -> str:
    if not src:
        return src

    src = re.sub(
        r"(<[^>]*?)\s+encoding=(?:\"[^\"]*\"|'[^']*'|[^\s>]+)",
        r"\1",
        src,
    )

    src = src.replace("--!>", "-->")
    src = re.sub(r"(<!-->|<!--->)", "<!-- -->", src)
    src = re.sub(r"</?o:.*?>", "", src)

    try:
        doc, single_body_element = fromstring(src)
    except etree.ParserError as e:
        if "empty" in str(e):
            return ""
        raise

    for el in doc.iter(tag=etree.Element):
        tag_quote(el)

    if filter_callback:
        doc = filter_callback(doc)

    src = html.tostring(doc, encoding="unicode", method=output_method)

    if not single_body_element and src.startswith("<div>") and src.endswith("</div>"):
        src = src[5:-6]

    return src.replace("\xa0", "&nbsp;")


@overload
def html_sanitize(
    src: None,
    silent: bool = True,
    sanitize_tags: bool = True,
    sanitize_attributes: bool = False,
    sanitize_style: bool = False,
    sanitize_form: bool = True,
    sanitize_conditional_comments: bool = True,
    strip_style: bool = False,
    strip_classes: bool = False,
    output_method: str = "html",
) -> None: ...


@overload
def html_sanitize(
    src: str | markupsafe.Markup,
    silent: bool = True,
    sanitize_tags: bool = True,
    sanitize_attributes: bool = False,
    sanitize_style: bool = False,
    sanitize_form: bool = True,
    sanitize_conditional_comments: bool = True,
    strip_style: bool = False,
    strip_classes: bool = False,
    output_method: str = "html",
) -> markupsafe.Markup: ...


def html_sanitize(
    src: str | markupsafe.Markup | None,
    silent: bool = True,
    sanitize_tags: bool = True,
    sanitize_attributes: bool = False,
    sanitize_style: bool = False,
    sanitize_form: bool = True,
    sanitize_conditional_comments: bool = True,
    strip_style: bool = False,
    strip_classes: bool = False,
    output_method: str = "html",
) -> markupsafe.Markup | None:
    if not src:
        return src

    logger = logging.getLogger(__name__ + ".html_sanitize")

    def sanitize_handler(doc: etree._Element, prestrip: bool = False) -> etree._Element:
        if prestrip and sanitize_tags:
            etree.strip_elements(doc, *SANITIZE_TAGS["kill_tags"], with_tail=False)
        kwargs = {
            "scripts": True,
            "javascript": True,
            "page_structure": True,
            "style": strip_style,
            "sanitize_style": sanitize_style,
            "forms": sanitize_form,
            "remove_unknown_tags": False,
            "comments": False,
            "conditional_comments": sanitize_conditional_comments,
            "processing_instructions": False,
        }
        if sanitize_tags:
            kwargs.update(SANITIZE_TAGS)

        if sanitize_attributes:
            if strip_classes:
                current_safe_attrs = safe_attrs - frozenset(["class"])
            else:
                current_safe_attrs = safe_attrs
            kwargs.update(
                {
                    "safe_attrs_only": True,
                    "safe_attrs": current_safe_attrs,
                }
            )
        else:
            kwargs.update(
                {
                    "safe_attrs_only": False,
                    "strip_classes": strip_classes,
                }
            )

        cleaner = _Cleaner(**kwargs)
        cleaner(doc)
        return doc

    try:
        sanitized = html_normalize(
            src, filter_callback=sanitize_handler, output_method=output_method
        )
    except etree.ParserError:
        if not silent:
            raise
        logger.warning("ParserError obtained when sanitizing %r", src, exc_info=True)
        sanitized = "<p>ParserError when sanitizing</p>"
    except Exception:
        if not silent:
            raise
        sanitized = None
        if sanitize_tags:
            try:
                sanitized = html_normalize(
                    src,
                    filter_callback=lambda doc: sanitize_handler(doc, prestrip=True),
                    output_method=output_method,
                )
            except Exception:
                sanitized = None
        if sanitized is None:
            logger.warning(
                "unknown error obtained when sanitizing %r", src, exc_info=True
            )
            sanitized = "<p>Unknown error when sanitizing</p>"

    return markupsafe.Markup(sanitized)


URL_SKIP_PROTOCOL_REGEX = r"mailto:|tel:|sms:"

_HREF_URL_SOURCE = rf"""(\bhref=['"](?!{URL_SKIP_PROTOCOL_REGEX})([^'"]+)['"])"""

URL_REGEX = re.compile(_HREF_URL_SOURCE)
TEXT_URL_REGEX = re.compile(r"https?://[\w@:%.+&~#=/-]+(?:\?\S+)?")
HTML_TAG_URL_REGEX = re.compile(_HREF_URL_SOURCE + r"([^<>]*>([^<>]+)<\/)?")
HTML_TAGS_REGEX = re.compile(r"<[^>]*>")
HTML_NEWLINES_REGEX = re.compile(r"<(div|p|br|tr)[^>]*>|\n")

_RUNS_OF_SPACE_OR_TAB_RE = re.compile(r" {2,}|\t")
_CLOSING_BODY_RE = re.compile(r"</body\s*>", re.IGNORECASE)
_CLOSING_HTML_RE = re.compile(r"</html\s*>", re.IGNORECASE)

_ICON_RE = re.compile(
    r'<\s*(i|span)\b(\s+[A-Za-z_-][A-Za-z0-9-_]*(\s*=\s*[\'"][^"\']*[\'"])?)*\s*\bclass\s*=\s*["\'][^"\']*\b(fa|fab|fad|far|oi)\b'
)
_EMPTY_TAG_RE = re.compile(
    r'<\s*\/?(?:p|div|section|span|br|b|i|font)\b(?:(\s+[A-Za-z_-][A-Za-z0-9-_]*(\s*=\s*[\'"][^"\']*[\'"]))*)(?:\s*>|\s*\/\s*>)'
)

_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL
)

_DOCUMENT_SHELL_RE = re.compile(r"(?i)(</?(?:html|body|head|!\s*DOCTYPE)[^>]*>)")

_SIGNATURE_BEGIN_RE = re.compile(r"((?:(?:^|\n)[-]{2}[\s]?$))")
_TEXT_COMPLETE_RE = re.compile(
    r"((?:\n[>]+[^\n\r]*)+|(?:(?:^|\n)[-]{2}[\s]?[\r\n]{1,2}[\s\S]+))"
)

_LINK_TAGS_RE = re.compile(
    r"""(?<!["'])((ftp|http|https):\/\/(\w+:{0,1}\w*@)?([^\s<"']+)(:[0-9]+)?(\/|\/([^\s<"']))?)(?![^\s<"']*["']|[^\s<"']*</a>)"""
)

_SIMPLE_TAG_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9]*$")

_BR_TAGS_RE = re.compile(r"(([<]\s*[bB][rR]\s*/?[>]\s*){2,})")


def normalize_url(url: str) -> str:
    if urlparse(url).scheme in ("http", "https", "ftp", "ftps"):
        return url
    if url.startswith(("?", "#")) or (url.startswith("/") and not url.startswith("//")):
        return url
    return "http://" + url


def is_html_empty(
    html_content: str | markupsafe.Markup | Literal[False] | None,
) -> bool:
    if not html_content:
        return True
    without_scripts = _SCRIPT_STYLE_RE.sub("", html_content)
    text_content = htmllib.unescape(_EMPTY_TAG_RE.sub("", without_scripts))
    return not bool(text_content.strip()) and not _ICON_RE.search(html_content)


def html_keep_url(text: str | Markup) -> Markup:
    idx = 0
    parts: list[Markup] = []
    for item in _LINK_TAGS_RE.finditer(text):
        parts.append(escape_silent(text[idx : item.start()]))
        url = text[item.start() : item.end()]
        parts.append(create_link(url, url))
        idx = item.end()
    parts.append(escape_silent(text[idx:]))
    return Markup("").join(parts)


def html_to_inner_content(source: str | markupsafe.Markup | None) -> str:
    if is_html_empty(source):
        return ""
    if not isinstance(source, markupsafe.Markup):
        source = html_sanitize(source) or ""
    processed = HTML_NEWLINES_REGEX.sub(" ", source)
    processed = HTML_TAGS_REGEX.sub("", processed)
    processed = _RUNS_OF_SPACE_OR_TAB_RE.sub(" ", processed)
    processed = processed.replace("\xa0", " ")
    processed = htmllib.unescape(processed)
    return processed.strip()


_LINK_SAFE_SCHEMES = frozenset({"http", "https", "ftp", "ftps", "mailto", "tel"})


def create_link(url: str, label: str) -> Markup:
    scheme = urlparse(url).scheme
    if scheme and scheme.lower() not in _LINK_SAFE_SCHEMES:
        url = "#"
    return Markup(
        '<a href="{}" target="_blank" rel="noreferrer noopener">{}</a>'
    ).format(url, label)


def _number_references(tree: etree._Element) -> list[str]:
    url_index: list[str] = []
    linkrefs = itertools.count(1)

    for link in tree.findall(".//a"):
        if url := link.get("href"):
            link.tag = "span"
            label = link.text or ""
            link.text = (
                f"{label} [{next(linkrefs)}]" if label else f"[{next(linkrefs)}]"
            )
            url_index.append(url)

    for img in tree.findall(".//img"):
        if src := img.get("src"):
            img.tag = "span"
            if src.startswith("data:"):
                img_name = None
            else:
                img_name = re.search(r"[^/]+(?=\.[a-zA-Z]+(?:\?|$))", src)
            img.text = f"{img_name[0] if img_name else 'Image'} [{next(linkrefs)}]"
            url_index.append(src)

    return url_index


def _markup_to_structured_text(tree: etree._Element) -> str:
    html_str = etree.tostring(tree, encoding="unicode")
    html_str = html_str.replace("&#13;", "")

    for tag, marker in (
        ("strong", "*"),
        ("b", "*"),
        ("h3", "*"),
        ("h2", "**"),
        ("h1", "**"),
        ("em", "/"),
    ):
        html_str = re.sub(rf"</?{tag}\b[^>]*>", marker, html_str)
    html_str = re.sub(r"<tr\b[^>]*>", "\n", html_str)
    html_str = re.sub(r"</p\s*>", "\n", html_str)
    html_str = re.sub(r"<br\s*/?>", "\n", html_str)
    html_str = re.sub(r"<[^>]*>", " ", html_str)
    html_str = html_str.replace(" " * 2, " ")
    html_str = html_str.replace("&gt;", ">")
    html_str = html_str.replace("&lt;", "<")
    html_str = html_str.replace("&amp;", "&")

    html_str = "\n".join([x.strip() for x in html_str.splitlines()])
    return html_str.replace("\n" * 2, "\n")


def html2plaintext(
    html_content: str | markupsafe.Markup | Literal[False] | None,
    body_id: str | None = None,
    encoding: str = "utf-8",
    include_references: bool = True,
) -> str:
    if not (html_content and html_content.strip()):
        return ""

    if isinstance(html_content, bytes):
        html_content = html_content.decode(encoding)
    else:
        assert isinstance(html_content, str), (
            f"expected str got {html_content.__class__.__name__}"
        )

    tree = etree.fromstring(html_content, parser=etree.HTMLParser())
    if tree is None:
        return ""

    if body_id is not None:
        source = tree.xpath("//*[@id=$body_id]", body_id=body_id)
        if not len(source):
            return ""
    else:
        source = tree.xpath("//body")
    if len(source):
        tree = source[0]

    url_index = _number_references(tree) if include_references else []
    html_str = _markup_to_structured_text(tree)

    if url_index:
        html_str += "\n\n"
        for i, url in enumerate(url_index, start=1):
            html_str += f"[{i}] {url}\n"

    return html_str.strip()


def plaintext2html(
    text: str, container_tag: str | None = None, with_paragraph: bool = True
) -> markupsafe.Markup:
    assert isinstance(text, str)
    text = html_escape(text)

    text = Markup(re.sub(r"(\r\n|\r|\n)", "<br/>", text))

    text = html_keep_url(text)

    final = text
    if with_paragraph:
        idx = 0
        paragraphs: list[Markup] = []
        for item in _BR_TAGS_RE.finditer(text):
            paragraphs.append(text[idx : item.start()])
            idx = item.end()
        paragraphs.append(text[idx:])
        final = Markup("<p>") + Markup("</p><p>").join(paragraphs) + Markup("</p>")

    if container_tag:
        if not _SIMPLE_TAG_RE.match(container_tag):
            e = f"Invalid container_tag: {container_tag!r}"
            raise ValueError(e)
        final = Markup(f"<{container_tag}>") + final + Markup(f"</{container_tag}>")
    return final


def add_html_content(
    html_body: str,
    content: str,
    plaintext: bool = True,
    preserve: bool = False,
    container_tag: str | None = None,
) -> markupsafe.Markup:
    if plaintext and preserve:
        content = f"\n<pre>{html_escape(content)}</pre>\n"
    elif plaintext:
        content = f"\n{plaintext2html(content, container_tag)}\n"
    else:
        content = _DOCUMENT_SHELL_RE.sub("", content)
        content = f"\n{content}\n"
    closing = _CLOSING_BODY_RE.search(html_body) or _CLOSING_HTML_RE.search(html_body)
    if closing is None:
        return markupsafe.Markup(f"{html_body}{content}")
    insert_location = closing.start()
    return markupsafe.Markup(
        f"{html_body[:insert_location]}{content}{html_body[insert_location:]}"
    )


def prepend_html_content(html_body: str, html_content: str | markupsafe.Markup) -> str:
    stripped = _DOCUMENT_SHELL_RE.sub("", html_content).strip()

    body_match = re.search(r"<body[^>]*>", html_body) or re.search(
        r"<html[^>]*>", html_body
    )
    insert_index = body_match.end() if body_match else 0

    if isinstance(html_body, markupsafe.Markup):
        html_content = type(html_content)(stripped)
        return html_body[:insert_index] + html_content + html_body[insert_index:]
    return f"{html_body[:insert_index]}{stripped}{html_body[insert_index:]}"


LOCAL_LINK_PATTERNS = (
    re.compile(r"""(<(?:img|v:fill|v:image)(?=\s)[^>]*\ssrc=")(/(?!/)[^"]*)"""),
    re.compile(r"""(<a(?=\s)[^>]*\shref=")(/(?!/)[^"]*)"""),
    re.compile(r"""(<[\w-]+(?=\s)[^>]*\sbackground=")(/(?!/)[^"]*)"""),
    re.compile(
        r"""(                            # 1: the element up to the url, opening quote included
            <[^>]+\bstyle=['"]           # an element carrying a style attribute
            [^'"]+\burl\(                # whose style contains url(
            (?:&\#34;|'|&quot;|&\#39;|")?  # the url may open with an (escaped) quote
        )(                               # 2: the url itself
            /(?!/)[^'")]*                # a local path; "//host" is not one
        )""",
        re.VERBOSE,
    ),
)


def replace_local_links(html_content: str, resolve_base_url: Callable[[], str]) -> str:
    if not html_content:
        return html_content

    wrapper = type(html_content)
    base_url = None

    def to_absolute(match: re.Match[str]) -> str:
        nonlocal base_url
        if base_url is None:
            base_url = resolve_base_url() or ""
        try:
            return match.group(1) + urljoin(base_url, match.group(2))
        except ValueError:
            return match.group(0)

    for pattern in LOCAL_LINK_PATTERNS:
        html_content = pattern.sub(to_absolute, html_content)

    return wrapper(html_content)
