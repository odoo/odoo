# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from typing import Callable


class BaseNode:
    def __init__(
        self,
        get_node: Callable,
        options: dict,
        indentation_level: int = 0,
        induce_indent: bool = False,
        induce_markup: str = "",
        require_before: str = "",
        require_after: str = "",
        starts_with_whitespace: bool = False,
        ends_with_whitespace: bool = False,
        cancels_previous_whitespace: bool = False,
        cancels_leading_tail_whitespace: bool = False,
        force_cancel_whitespace: bool = False,
        verbose: bool = False,
        position=None,
    ):
        self.get_node = get_node
        self.options = options
        self.induce_indent = induce_indent
        self.induce_markup = induce_markup
        self.require_before = require_before  # Also means discarding whitespace before it
        self.require_after = require_after
        self.starts_with_whitespace = starts_with_whitespace
        self.ends_with_whitespace = ends_with_whitespace
        self.position = position
        self.cancels_previous_whitespace = cancels_previous_whitespace or force_cancel_whitespace
        self.cancels_leading_tail_whitespace = cancels_leading_tail_whitespace
        self.verbose = verbose
        self.indentation_level = indentation_level

    def __str__(self):
        return json.dumps(
            {self.__class__.__name__: self.get_str_components()},
            indent=2,
        )

    def get_str_components(self):
        components = {}
        if self.starts_with_whitespace:
            components.update(starts_with_whitespace=True)
        if self.ends_with_whitespace:
            components.update(ends_with_whitespace=True)
        if self.require_after:
            components.update(require_after=self.require_after)
        if self.require_before:
            components.update(require_before=self.require_before)
        if self.indentation_level:
            components.update(indentation_level=self.indentation_level)
        return components

    def to_text_node(self, converter_state):
        raise NotImplementedError

    def to_markdown(self, converter_state) -> str:
        raise NotImplementedError
