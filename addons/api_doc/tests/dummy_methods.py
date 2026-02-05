from odoo import api, models
from odoo.api import Self


class DummyMethods:
    def one_arg(self, a: int) -> int:
        """
        A simple dummy identity function.

        :param int a: an int.
        :returns: an int.
        :rtype: int
        """
        return a

    one_arg.expected = {
        "signature": "(a) -> int",
        "parameters": {
            "a": {"annotation": "int", "doc": "<p>an int.</p>"},
        },
        "return": {"annotation": "int", "doc": "<p>an int.</p>"},
        "doc": """
        <div class="document">
        <p>A simple dummy identity function.</p>
        </div>""",
    }

    def multiple_args_and_error(self, a: int, b: list[int], c: dict[str, list[str]]) -> int:
        """
        Another dummy function.

        :param int a: an int.
        :param list[int] b: a list of int.
        :param dict[str, list[str]] c: a dict of lists.
        :raises ValueError: raise an error if ``a`` is greater than ``len(b)``.
        :returns: returns the element of ``b`` at index ``a``.
        :rtype: int
        """
        return a

    multiple_args_and_error.expected = {
        "signature": "(a, b, c) -> int",
        "parameters": {
            "a": {"annotation": "int", "doc": "<p>an int.</p>"},
            "b": {"annotation": "list[int]", "doc": "<p>a list of int.</p>"},
            "c": {"annotation": "dict[str, list[str]]", "doc": "<p>a dict of lists.</p>"},
        },
        'raise': {'ValueError': '<p>raise an error if <tt class="docutils literal">a</tt> is greater than <tt class="docutils literal">len(b)</tt>.</p>'},
        "return": {"annotation": "int", "doc": '<p>returns the element of <tt class="docutils literal">b</tt> at index <tt class="docutils literal">a</tt>.</p>'},
        "doc": """
        <div class="document">
        <p>Another dummy function.</p>
        </div>""",
    }

    def docstring_but_no_hints(self, a, b):
        """
        :param a: an A
        :param b: a B
        """
        pass

    docstring_but_no_hints.expected = {
        "signature": "(a, b)",
        "parameters": {
            "a": {"doc": "<p>an A</p>"},
            "b": {"doc": "<p>a B</p>"},
        },
        "doc": '<div class="document"></div>',
    }

    def no_docstring_but_hints(self, a: int) -> int:
        return a

    no_docstring_but_hints.expected = {
        "signature": "(a) -> int",
        "parameters": {"a": {"annotation": "int"}},
        "return": {"annotation": "int"},
    }

    # the cls param should be stripped away
    @classmethod
    def class_method(cls, a):
        """
        :param a: an A
        """
        pass

    class_method.__func__.expected = {
        'signature': '(a)',
        'parameters': {'a': {'doc': '<p>an A</p>'}},
        'doc': '<div class="document"></div>'
    }

    # the self param should be stripped away
    def self_method(self, a):
        """
        :param self:
        :param a: an A
        """
        pass

    self_method.expected = {
        "signature": "(a)",
        "parameters": {"a": {"doc": "<p>an A</p>"}},
        "doc": '<div class="document"></div>',
    }

    # BaseModel should be replaced by list[int]
    def returns_base_model(self) -> models.BaseModel:
        """
        :rtype: BaseModel
        """
        return object.__new__(models.BaseModel)

    returns_base_model.expected = {
        "signature": "() -> list[int]",
        "parameters": {},
        "return": {"annotation": "list[int]"},
        "doc": '<div class="document"></div>',
    }

    # Model should be replaced by list[int]
    def returns_model(self) -> models.Model:
        """
        :rtype: Model
        """
        return object.__new__(models.Model)

    returns_model.expected = {
        "signature": "() -> list[int]",
        "parameters": {},
        "return": {"annotation": "list[int]"},
        "doc": '<div class="document"></div>',
    }

    # Self should be replaced by list[int]
    def returns_self(self) -> Self:
        """
        :rtype: Self
        """
        return self

    returns_self.expected = {
        "signature": "() -> list[int]",
        "parameters": {},
        "return": {"annotation": "list[int]"},
        "doc": '<div class="document"></div>',
    }

    @api.model
    def api_model_decorator(self):
        pass

    api_model_decorator.expected = {"api": ["model"], "parameters": {}, "signature": "()"}

    @api.readonly
    def api_readonly_decorator(self):
        pass

    api_readonly_decorator.expected = {"api": ["readonly"], "parameters": {}, "signature": "()"}

    @api.model
    @api.readonly
    def multiple_decorators(self):
        pass

    multiple_decorators.expected = {"signature": "()", "parameters": {}, "api": ["model", "readonly"]}

    def bulletpoints(self):
        """
        Some bulletpoints:

        * beep
        * boop

        a bit more text
        """
        pass

    bulletpoints.expected = {
        "signature": "()",
        "parameters": {},
        "doc": """
        <div class="document">
        <p>Some bulletpoints:</p>
        <ul class="simple">
        <li>beep</li>
        <li>boop</li>
        </ul>
        <p>a bit more text</p>
        </div>""",
    }
