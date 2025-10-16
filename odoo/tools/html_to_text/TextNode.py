# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from .BaseNode import BaseNode
from .constants import BEFORE_EOL, SURROUNDING_WHITESPACE_REGEX

SIMPLE_WHITESPACE = re.compile(r"[ \n\r\t]+")


def get_no_node(tag, options, **kwargs):
    return None


class TextNode(BaseNode):
    @staticmethod
    def from_text(start_text: str, position: int = 0, **kwargs):
        """Return a TextNode instance from a given text input and metadata."""
        keep_original_whitespace = kwargs.pop("keep_original_whitespace", False)
        before_eol = kwargs.pop("before_eol", BEFORE_EOL)
        if start_text.isspace():
            pre, text, post = "", "", start_text
        else:
            with_whitespace = SURROUNDING_WHITESPACE_REGEX.match(start_text)
            if with_whitespace:
                pre, text, post = with_whitespace.groups()
                if not keep_original_whitespace:
                    text = re.sub(SIMPLE_WHITESPACE, " ", text)
                elif before_eol:
                    # Render newlines correctly
                    text = re.sub(r"\n", f"{before_eol}\n", text)
            else:
                raise ValueError("Match Not Found with text", start_text)

        return TextNode(
            content=text,
            position=position,
            starts_with_whitespace=bool(pre),
            ends_with_whitespace=bool(post),
            **kwargs,
        )

    def __init__(self, content: str, **kwargs):
        super().__init__(get_no_node, {}, **kwargs)
        self._content: str = content

    @property
    def content(self):
        return self._content

    def to_text_node(self, renderer_state) -> "TextNode":
        if self.require_after:
            self.ends_with_whitespace = False
        return self

    def concatenate(self, other: "TextNode", separator="", suffix=""):
        between = self.get_separator(other, separator)
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

    def get_separator(self, b: "TextNode", separator="") -> str:
        first = (
            " "
            if (not self._content or not self._content[-1].isspace())
            and (not b._content or not b._content[-1].isspace())
            and (not b.cancels_previous_whitespace and (self.ends_with_whitespace or b.starts_with_whitespace))
            else ""
        )
        second = (
            "\n\n"
            if self.require_after == "\n\n" or b.require_before == "\n\n"
            else merge_requirements(self.require_after, b.require_before)
            if not self.content.endswith("\n\n")
            else ""
        )
        return first + second + separator


def merge_requirements(after_a: str, before_b: str) -> str:
    """Compile the final separation string matching requirements for nodes A and B.

    :param after_a: Segment that must come after node A.
    :param before_b: Segment that must precede node B.
    :return: The merged separator string
    """
    remaining_start, remaining_end = after_a, before_b
    final_start, final_end_reversed = [], []

    while True:
        # Handle "\n" consuming " "
        if remaining_start.endswith("\n") and remaining_end.startswith(" "):
            remaining_end = remaining_end.lstrip(" ")
        elif remaining_end.startswith("\n") and remaining_start.endswith(" "):
            remaining_start = remaining_start.rstrip(" ")

        if not remaining_start or remaining_end.startswith(remaining_start):
            final_end_reversed.append(remaining_end)
            break
        if not remaining_end or remaining_start.endswith(remaining_end):
            final_start.append(remaining_start)
            break

        # Compare boundary characters to decide how to shrink while accumulating final_start/final_end.
        remaining_start_first = remaining_start[0]
        remaining_end_last = remaining_end[-1]

        if remaining_start_first == remaining_end_last or remaining_end_last != remaining_start[-1]:
            final_end_reversed.append(remaining_end_last)
            remaining_end = remaining_end[:-1]

        if remaining_start_first != remaining_end_last:
            final_start.append(remaining_start_first)
            remaining_start = remaining_start[1:]

    return "".join(final_start + final_end_reversed[::-1])
