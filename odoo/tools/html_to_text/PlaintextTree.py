# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import textwrap

import lxml

from .constants import BEFORE_EOL, LINK_TAG_REGEX
from .NodeWithChildren import RootNode


class PlaintextTree:
    # noinspection PyProtectedMember
    def __init__(self, root_html_node: lxml.etree._Element, get_node):
        self.root_html = root_html_node
        self.get_node = get_node
        self.inline_tags = {}  # current default Odoo behavior for links
        self.before_eol = BEFORE_EOL
        self.state = RendererState()

    def render_plaintext(self, options=None) -> str:
        self.state.reset()

        options = options or {}

        if (before_eol := options.get("before_eol")) is not None:
            self.before_eol = before_eol

        self.inline_tags["a"] = options.get("inline_links", False)
        self.inline_tags["img"] = options.get("inline_images", False)
        root_converter_node = self._get_converter_root_node(options)

        markdown = root_converter_node.to_plaintext(self.state).strip()
        if self.state.has_links:
            markdown = self._render_links(markdown)

        if max_width := options.get("line_width"):
            return self._apply_line_width(markdown, max_width)
        return markdown

    def _render_links(self, markdown) -> str:
        footnote_links = []
        position = 1

        # Make sure we convert links in order of reading, in a single pass
        def _replace(match):
            nonlocal position
            link_key = match.group()
            link = self.state.get_link(link_key)
            inline, footnote = link.render(self.inline_tags[link.tag], position)
            if not self.inline_tags[link.tag]:
                footnote_links.append(footnote)
                position += 1
            return inline

        markdown = re.sub(LINK_TAG_REGEX, _replace, markdown)
        if footnote_links:
            markdown += "\n\n\n" + f"{self.before_eol}\n".join(footnote_links)

        return markdown

    def _get_converter_root_node(self, options: dict | None = None) -> RootNode:
        return RootNode(self.get_node, options or {}, self.root_html)

    def _apply_line_width(self, markdown: str, max_width: int) -> str:
        """Wrap all lines in the given Markdown to the specified max width."""
        new_markdown_lines = []
        for line in markdown.splitlines():
            new_markdown_lines += self._wrap_line(line, max_width)
        return "\n".join(new_markdown_lines)

    @staticmethod
    def _wrap_line(line: str, max_width: int) -> list[str]:
        """Wrap a single line of text to the specified maximum width.

        It preserves the original indentation of the line, ensuring that the leading whitespace
        is respected, and later lines are properly indented to match.

        :param line: The line of text to be wrapped.
        :param max_width: The maximum width for each line after wrapping.
        :return: A list of strings where each string is a wrapped line.
        """
        if len(line) <= max_width:
            return [line]
        without_leading_whitespace = line.lstrip()
        indent_chars = len(line) - len(without_leading_whitespace)
        return textwrap.wrap(line, width=max_width, initial_indent="", subsequent_indent=" " * indent_chars)


class RendererState:
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
