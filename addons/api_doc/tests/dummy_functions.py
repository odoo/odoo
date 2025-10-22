from typing import Self

from odoo import api, models


class DummyFunctions:
    def one_arg(self, a: int) -> int:
        """
        A simple dummy identity function.

        :param int a: an int.
        :returns: an int.
        :rtype: int
        """
        return a

    def multiple_args_and_error(self, a: int, b: list[int]) -> int:
        """
        Another dummy function,
        :param int a: an int.
        :param list[int] b: a list of int
        :raises ValueError: raise an error if `a` is greater than `len(b)`.
        :returns: returns the element of `b` at index `a`.
        :rtype: int
        """
        return a

    def docsring_but_no_hints(self, a, b):
        """
        :param a: an A
        :param b: a B
        """
        pass

    def no_docstring_but_hints(self, a: int) -> int:
        return a

    # the cls param should be stripped away
    @classmethod
    def class_method(cls, a):
        """
        :param cls:
        :param a: an A
        """
        pass

    # the self param should be stripped away
    def self_method(self, a):
        """
        :param self:
        :param a: an A
        """
        pass

    # BaseModel should be replaced by list[int]
    def returns_base_model(self) -> models.BaseModel:
        """
        :rtype: BaseModel
        """
        return object.__new__(models.BaseModel)

    # Model should be replaced by list[int]
    def returns_model(self) -> models.Model:
        """
        :rtype: Model
        """
        return object.__new__(models.Model)

    # Self should be replaced by list[int]
    def returns_self(self) -> Self:
        """
        :rtype: Self
        """
        return self

    @api.model
    def api_model_decorator(self):
        pass

    @api.readonly
    def api_readonly_decorator(self):
        pass

    @api.model
    @api.readonly
    def multiple_decorators(self):
        pass

    def bulletpoints(self):
        """
        Some bulletpoints:

        * beep
        * boop

        a bit more text
        """
        pass


TEST_DOCSTRINGS = {
    "one_arg": {
        'signature': '(a) -> int',
        'parameters': {
            'a': {'annotation': 'int', 'doc': '<p>an int.</p>'},
        },
        'return': {'annotation': 'int', 'doc': '<p>an int.</p>'},
        'doc': '<div class="document">\n\n\n<p>A simple dummy identity function.</p>\n</div>',
    },
    "multiple_args_and_error": {
        "signature": "(a, b) -> int",
        "parameters": {
            "a": {"annotation": "int"},
            "b": {"annotation": "list[int]"},
        },
        "return": {"annotation": "int"},
        "doc": '<div class="document">\n\n\n<p>Another dummy function,\n:param int a: an int.\n:param list[int] b: a list of int\n:raises ValueError: raise an error if <cite>a</cite> is greater than <cite>len(b)</cite>.\n:returns: returns the element of <cite>b</cite> at index <cite>a</cite>.\n:rtype: int</p>\n</div>',
    },
    "docsring_but_no_hints": {
        "signature": "(a, b)",
        "parameters": {"a": {}, "b": {}},
        "doc": '<div class="document">\n\n<table class="docinfo" frame="void" rules="none">\n<col class="docinfo-name" />\n<col class="docinfo-content" />\n<tbody valign="top">\n<tr class="param-a field"><th class="docinfo-name">param a:</th><td class="field-body">an A</td>\n</tr>\n<tr class="param-b field"><th class="docinfo-name">param b:</th><td class="field-body">a B</td>\n</tr>\n</tbody>\n</table>\n\n</div>',
    },
    "no_docstring_but_hints": {
        "signature": "(a) -> int",
        "parameters": {"a": {"annotation": "int"}},
        "return": {"annotation": "int"},
    },
    "class_method": {
        "signature": "(a)",
        "parameters": {"a": {}},
        "doc": '<div class="document">\n\n<table class="docinfo" frame="void" rules="none">\n<col class="docinfo-name" />\n<col class="docinfo-content" />\n<tbody valign="top">\n<tr class="param-cls field"><th class="docinfo-name">param cls:</th><td class="field-body"></td>\n</tr>\n<tr class="param-a field"><th class="docinfo-name">param a:</th><td class="field-body">an A</td>\n</tr>\n</tbody>\n</table>\n\n</div>',
    },
    "self_method": {
        "signature": "(a)",
        "parameters": {"a": {}},
        "doc": '<div class="document">\n\n<table class="docinfo" frame="void" rules="none">\n<col class="docinfo-name" />\n<col class="docinfo-content" />\n<tbody valign="top">\n<tr class="param-self field"><th class="docinfo-name">param self:</th><td class="field-body"></td>\n</tr>\n<tr class="param-a field"><th class="docinfo-name">param a:</th><td class="field-body">an A</td>\n</tr>\n</tbody>\n</table>\n\n</div>',
    },
    "returns_base_model": {
        "signature": "() -> list[int]",
        "parameters": {},
        "return": {"annotation": 'list[int]'},
        "doc": '<div class="document">\n\n<table class="docinfo" frame="void" rules="none">\n<col class="docinfo-name" />\n<col class="docinfo-content" />\n<tbody valign="top">\n<tr class="rtype field"><th class="docinfo-name">rtype:</th><td class="field-body">BaseModel</td>\n</tr>\n</tbody>\n</table>\n\n</div>',
    },
    "returns_model": {
        "signature": "() -> list[int]",
        "parameters": {},
        "return": {"annotation": 'list[int]'},
        "doc": '<div class="document">\n\n<table class="docinfo" frame="void" rules="none">\n<col class="docinfo-name" />\n<col class="docinfo-content" />\n<tbody valign="top">\n<tr class="rtype field"><th class="docinfo-name">rtype:</th><td class="field-body">Model</td>\n</tr>\n</tbody>\n</table>\n\n</div>',
    },
    "returns_self": {
        "signature": "() -> list[int]",
        "parameters": {},
        "return": {"annotation": 'list[int]'},
        "doc": '<div class="document">\n\n<table class="docinfo" frame="void" rules="none">\n<col class="docinfo-name" />\n<col class="docinfo-content" />\n<tbody valign="top">\n<tr class="rtype field"><th class="docinfo-name">rtype:</th><td class="field-body">Self</td>\n</tr>\n</tbody>\n</table>\n\n</div>',
    },
    "api_model_decorator": {"api": ["model"], "parameters": {}, "signature": "()"},
    "api_readonly_decorator": {"api": ["readonly"], "parameters": {}, "signature": "()"},
    "multiple_decorators": {"signature": "()", "parameters": {}, "api": ["model", "readonly"]},
    "bulletpoints": {
        "signature": "()",
        "parameters": {},
        "doc": '<div class="document">\n\n\n<p>Some bulletpoints:</p>\n<ul class="simple">\n<li>beep</li>\n<li>boop</li>\n</ul>\n<p>a bit more text</p>\n</div>',
    },
}
