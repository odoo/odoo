from typing import Collection, Iterable, Literal, Pattern, TypeVar, overload

from lxml.etree import _ElementTree
from lxml.html import HtmlElement

# For methods generating output from input data, their types would match
_DT = TypeVar("_DT", str, bytes, HtmlElement)
_ET_DT = TypeVar("_ET_DT", str, bytes, HtmlElement, _ElementTree[HtmlElement])


def _get_authority_from_url(url: str) -> str | None: ...


class LXMLHTMLCleanWarning(Warning):
    pass


class AmbiguousURLWarning(LXMLHTMLCleanWarning):
    pass


class Cleaner:
    @overload  # allow_tags present, remove_unknown_tags must be False
    def __init__(
        self,
        *,
        scripts: bool = True,
        javascript: bool = True,
        comments: bool = True,
        style: bool = False,
        inline_style: bool | None = None,
        links: bool = True,
        meta: bool = True,
        page_structure: bool = True,
        processing_instructions: bool = True,
        embedded: bool = True,
        frames: bool = True,
        forms: bool = True,
        annoying_tags: bool = True,
        remove_tags: Collection[str] = (),
        allow_tags: Collection[str] = (),
        kill_tags: Collection[str] = (),
        remove_unknown_tags: Literal[False] = False,
        safe_attrs_only: bool = True,
        safe_attrs: Collection[str] = ...,
        add_nofollow: bool = False,
        host_whitelist: Collection[str] = (),
        whitelist_tags: Collection[str] | None = {"iframe", "embed"},
    ) -> None: ...
    @overload  # ... otherwise, allow_tags must not be used
    def __init__(
        self,
        *,
        scripts: bool = True,
        javascript: bool = True,
        comments: bool = True,
        style: bool = False,
        inline_style: bool | None = None,
        links: bool = True,
        meta: bool = True,
        page_structure: bool = True,
        processing_instructions: bool = True,
        embedded: bool = True,
        frames: bool = True,
        forms: bool = True,
        annoying_tags: bool = True,
        remove_tags: Collection[str] = (),
        kill_tags: Collection[str] = (),
        remove_unknown_tags: bool = True,
        safe_attrs_only: bool = True,
        safe_attrs: Collection[str] = ...,
        add_nofollow: bool = False,
        host_whitelist: Collection[str] = (),
        whitelist_tags: Collection[str] = {"iframe", "embed"},
    ) -> None: ...
    def __call__(self, doc: HtmlElement | _ElementTree[HtmlElement]) -> None: ...
    def allow_follow(self, anchor: HtmlElement) -> bool: ...
    def allow_element(self, el: HtmlElement) -> bool: ...
    def allow_embedded_url(self, el: HtmlElement, url: str) -> bool: ...
    def kill_conditional_comments(self, doc: HtmlElement | _ElementTree[HtmlElement]) -> None: ...
    def clean_html(self, html: _ET_DT) -> _ET_DT: ...

clean: Cleaner
clean_html = clean.clean_html

def autolink(
    el: HtmlElement,
    link_regexes: Iterable[Pattern[str]] = ...,
    avoid_elements: Collection[str] = ...,
    avoid_hosts: Iterable[Pattern[str]] = ...,
    avoid_classes: Collection[str] = ["nolink"],
) -> None: ...
def autolink_html(
    html: _DT,
    link_regexes: Iterable[Pattern[str]] = ...,
    avoid_elements: Collection[str] = ...,
    avoid_hosts: Iterable[Pattern[str]] = ...,
    avoid_classes: Collection[str] = ["nolink"],
) -> _DT: ...
def word_break(
    el: HtmlElement,
    max_width: int = 40,
    avoid_elements: Collection[str] = ["pre", "textarea", "code"],
    avoid_classes: Collection[str] = ["nobreak"],
    break_character: str = chr(0x200B),
) -> None: ...
def word_break_html(
    html: _DT,
    max_width: int = 40,
    avoid_elements: Collection[str] = ["pre", "textarea", "code"],
    avoid_classes: Collection[str] = ["nobreak"],
    break_character: str = chr(0x200B),
) -> _DT: ...
