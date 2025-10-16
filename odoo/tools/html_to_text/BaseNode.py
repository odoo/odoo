# Part of Odoo. See LICENSE file for full copyright and licensing details.

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class BaseNode(ABC):
    # Class defaults, lowercase equivalent instance values can be different from initialization or update
    DEFAULT_REQUIRE_BEFORE: str = ""  # Also means discarding whitespace before it
    DEFAULT_REQUIRE_AFTER: str = ""
    DEFAULT_CANCELS_PREVIOUS_WHITESPACE: bool = False
    DEFAULT_INDUCE_INDENT: bool = False

    def __init__(
        self,
        get_node: Callable,
        options: dict[str, Any],
        indentation_level: int | None = None,
        induce_indent: bool | None = None,
        require_before: str | None = None,
        require_after: str | None = None,
        starts_with_whitespace: bool | None = False,
        ends_with_whitespace: bool | None = False,
        cancels_previous_whitespace: bool | None = False,
        force_cancel_whitespace: bool | None = False,
        position=None,
    ):
        self.get_node = get_node
        self.options = options
        self.indentation_level = (
            indentation_level if indentation_level is not None else options.get("indentation_level", 0)
        )
        self.induce_indent = induce_indent if induce_indent is not None else self.DEFAULT_INDUCE_INDENT
        self.require_before = self._get_require_before(
            options, require_before,
        )  # Also means discarding whitespace before it
        self.require_after = self._get_require_after(options, require_after)
        self.starts_with_whitespace = starts_with_whitespace
        self.ends_with_whitespace = ends_with_whitespace
        self.position = position
        self.cancels_previous_whitespace = (
            cancels_previous_whitespace or self.DEFAULT_CANCELS_PREVIOUS_WHITESPACE or force_cancel_whitespace
        )

    def to_plaintext(self, renderer_state) -> str:
        text_node = self.to_text_node(renderer_state)
        return text_node.content

    @abstractmethod
    def to_text_node(self, renderer_state):
        pass

    def _get_require_after(self, options: dict, require_after=None):
        if require_after is not None:
            return require_after
        return options.get("require_after", self.DEFAULT_REQUIRE_AFTER)

    def _get_require_before(self, options: dict, require_before=None):
        if require_before is not None:
            return require_before
        return options.get("require_before", self.DEFAULT_REQUIRE_BEFORE)
