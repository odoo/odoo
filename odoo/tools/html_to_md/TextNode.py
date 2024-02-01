# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .BaseNode import BaseNode
from .constants import ALL_WHITESPACE, SURROUNDING_WHITESPACE_REGEX


class TextNode(BaseNode):
    def __init__(self, content: str, **kwargs):
        super().__init__(lambda: False, {}, **kwargs)
        self._content: str = content

    @property
    def content(self):
        return self._content

    def get_str_components(self):
        components = super().get_str_components()
        components.update(content=self._content)
        return components

    def to_text_node(self, converter_state) -> "TextNode":
        if self.require_after:
            self.ends_with_whitespace = False
        return self

    def concatenate(self, other: "TextNode", separator="", suffix=""):
        between = get_separator(self, other, separator)
        self._content += f"{between}{other.content}{suffix}"
        self.ends_with_whitespace = other.ends_with_whitespace
        self.require_after = other.require_after
        return self

    def prepend(self, prefix):
        self._content = prefix + self._content

    def append(self, suffix):
        self._content += suffix

    def prepend_lines(self, prefix) -> None:
        """Prepend prefix on each line of self's content.

        :param prefix: Generally whitespace
        """
        trailing_newline = "\n" if self._content.endswith("\n") else ""
        content = self._content.rstrip("\n")
        self._content = prefix + f"\n{prefix}".join(content.split("\n")) + trailing_newline


def get_separator(a: TextNode, b: TextNode, separator=""):
    first = (
        " "
        if (not a._content or not a._content[-1].isspace())
        and (not b._content or not b._content[-1].isspace())
        and (not b.cancels_previous_whitespace and (a.ends_with_whitespace or b.starts_with_whitespace))
        else ""
    )
    second = (
        "\n\n"
        if a.require_after == "\n\n" or b.require_before == "\n\n"
        else merge_required(a.require_after, b.require_before)
        if not a.content.endswith("\n\n")
        else ""
    )
    return first + second + separator


def merge_required(a_required_after: str, b_required_before: str, start="", end="") -> str:
    if not a_required_after or b_required_before.startswith(a_required_after):
        return start + b_required_before + end
    if not b_required_before or a_required_after.endswith(b_required_before):
        return start + a_required_after + end

    if (a0 := a_required_after[0]) != b_required_before[0]:
        if (bl := b_required_before[-1]) != a_required_after[-1]:
            return merge_required(a_required_after[1:], b_required_before[:-1], start=start + a0, end=bl + end)
        return merge_required(a_required_after[1:], b_required_before, start=start + a0, end=end)

    bl = b_required_before[-1]
    return merge_required(a_required_after, b_required_before[:-1], start=start, end=bl + end)


def text_to_text_node(
    start_text,
    position=0,
    indentation_level=0,
    force_cancel_whitespace=False,
    verbose=False,
):
    all_whitespace = ALL_WHITESPACE.match(start_text)
    if all_whitespace:
        pre, text, post = "", "", start_text
    else:
        with_whitespace = SURROUNDING_WHITESPACE_REGEX.match(start_text)
        if with_whitespace:
            pre, text, post = with_whitespace.groups()
        else:
            raise ValueError("Match Not Found with text", start_text)

    return TextNode(
        content=text,
        position=position,
        starts_with_whitespace=bool(len(pre)),
        ends_with_whitespace=bool(len(post)),
        indentation_level=indentation_level,
        verbose=verbose,
        force_cancel_whitespace=force_cancel_whitespace,
    )
