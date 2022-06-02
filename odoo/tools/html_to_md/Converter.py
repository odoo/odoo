# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import textwrap
from typing import Collection, List

import lxml

from .NodeWithChildren import RootNode
from .constants import LINK_TAG_REGEX


class MarkdownConverter:
    # noinspection PyProtectedMember
    def __init__(self, root_html_node: lxml.etree._Element, get_node):
        self.root_html = root_html_node
        self.get_node = get_node
        self.inline_tags = {}  # current default Odoo behavior for links
        self.state = MarkdownConverterState()

    def render_markdown(self, verbose=False, options=None, flags=None) -> str:
        self.state.reset()

        options = self.merge_and_apply_options(options, flags)

        root_converter_node = self._get_converter_root_node(options, verbose=verbose)
        if verbose:
            print(str(root_converter_node))

        markdown = root_converter_node.to_markdown(self.state).strip()
        if self.state.has_links:
            markdown = self._convert_links(markdown)

        if max_width := options.get("line_width"):
            new_markdown_lines = []
            for line in markdown.splitlines():
                new_markdown_lines += self._wrap_line(line, max_width)
            return "\n".join(new_markdown_lines)

        return markdown

    def merge_and_apply_options(self, options: dict = None, flags: Collection[str] = None):
        options = options or {}

        self.inline_tags["a"] = options.get("inline_links", False)
        self.inline_tags["img"] = options.get("inline_images", False)

        if options.get("inline_images"):
            options["keep_images"] = True

        if flags:
            if "SIMPLE_LINE_ENDING" in flags:
                options["line_ending"] = ""
            if "INLINE_LINKS" in flags:
                self.inline_tags["a"] = True
            if "KEEP_IMAGES" in flags:
                options["keep_images"] = True
            if "INLINE_IMAGES" in flags:
                options["keep_images"] = True
                options["inline_images"] = True
                self.inline_tags["img"] = True
            if "80_CHARS" in flags:
                options["line_width"] = 80
            if "72_CHARS" in flags:
                options["line_width"] = 72

        return options

    def _convert_links(self, markdown) -> str:
        footnote_links = []
        position = 1
        # Make sure we convert links in order of reading
        for match in re.finditer(LINK_TAG_REGEX, markdown):
            link_key = match.group()
            link = self.state.get_link(link_key)
            inline, footnote = link.render(self.inline_tags[link.tag], position)
            markdown = markdown.replace(link_key, inline)
            if not self.inline_tags[link.tag]:
                footnote_links.append("   " + footnote)
                position += 1

        if footnote_links:
            markdown += "\n\n" + "  \n".join(footnote_links)

        return markdown

    def _get_converter_root_node(self, options: dict = None, verbose: bool = False) -> RootNode:
        return RootNode(self.get_node, options or {}, self.root_html, verbose)

    @staticmethod
    def _wrap_line(line: str, max_width: int) -> List[str]:
        if len(line) <= max_width:
            return [line]
        without_leading_whitespace = line.lstrip()
        indent_chars = len(line) - len(without_leading_whitespace)
        return textwrap.wrap(line, width=max_width, initial_indent="", subsequent_indent=" " * indent_chars)


class MarkdownConverterState:
    def __init__(self):
        self._links = {}

    def reset(self):
        self._links = {}

    def add_link(self, link):
        self._links[link.key] = link

    def get_link(self, key):
        return self._links[key]

    @property
    def has_links(self):
        return bool(len(self._links))
