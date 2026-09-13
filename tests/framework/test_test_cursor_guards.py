import ast
import inspect

import odoo.init  # noqa: F401  imported for the bootstrap side effect
from odoo.tests import cursor as cursor_mod


def test_the_guards_are_raises_not_asserts():
    # `python -O` strips `assert`; a closed test cursor must still refuse a
    # statement, and a cursor opened outside a test must still be refused.
    tree = ast.parse(inspect.getsource(cursor_mod))
    asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    assert asserts == []


def test_a_closed_test_cursor_refuses_a_statement_with_the_cursor_error():
    import psycopg
    import pytest

    tc = cursor_mod.TestCursor.__new__(cursor_mod.TestCursor)
    tc._closed = True
    with pytest.raises(psycopg.InterfaceError, match="closed"):
        tc._statement("execute", ("SELECT 1",), {})
