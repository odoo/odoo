import typing
from collections import namedtuple

from odoo.tests import TransactionCase

from .. import generalutils


class TestGeneralUtils(TransactionCase):
    def test_is_namedtuple(self):
        self.assertFalse(generalutils.is_namedtuple(["a list"]))
        self.assertFalse(generalutils.is_namedtuple(("a normal tuple",)))
        a_namedtuple = namedtuple("a_namedtuple", ["some_string"])
        self.assertTrue(generalutils.is_namedtuple(a_namedtuple("a namedtuple")))

        class AnotherNamedtuple(typing.NamedTuple):
            some_string: str

        self.assertTrue(
            generalutils.is_namedtuple(AnotherNamedtuple("a subclassed namedtuple"))
        )

    def test_varmap(self):
        top = {
            "middle": [
                "a list",
                "that contains",
                "the outer dict",
            ],
        }
        top["middle"].append(top)

        def func(_, two):
            return two

        # Don't care about the result, just that we don't get a recursion error
        generalutils.varmap(func, top)

    def test_get_environ(self):
        fake_environ = {
            "REMOTE_ADDR": None,
            "SERVER_PORT": None,
            "FORBIDDEN_VAR": None,
        }
        self.assertEqual(
            ["REMOTE_ADDR", "SERVER_PORT"],
            list(key for key, _ in generalutils.get_environ(fake_environ)),
        )
