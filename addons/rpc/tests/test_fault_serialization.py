import xmlrpc.client
from contextlib import contextmanager
from types import SimpleNamespace

import psycopg
from markupsafe import Markup

from odoo import exceptions
from odoo.http import _request_stack
from odoo.http import settings as http_settings
from odoo.tests import TransactionCase, tagged
from odoo.tools import lazy

from odoo.addons.base.models.res_lang import LangData
from odoo.addons.rpc.controllers.xmlrpc import (
    RPC_FAULT_CODE_ACCESS_DENIED,
    RPC_FAULT_CODE_ACCESS_ERROR,
    RPC_FAULT_CODE_APPLICATION_ERROR,
    RPC_FAULT_CODE_WARNING,
    dumps,
    xmlrpc_handle_exception_int,
    xmlrpc_handle_exception_string,
)


@tagged("post_install", "-at_install")
class TestFaultSerialization(TransactionCase):
    def _fault_from(self, payload):
        with self.assertRaises(xmlrpc.client.Fault) as capture:
            xmlrpc.client.loads(payload)
        return capture.exception

    def test_int_fault_codes_per_exception_type(self):
        cases = [
            (exceptions.AccessError("no access"), RPC_FAULT_CODE_ACCESS_ERROR),
            (exceptions.AccessDenied(), RPC_FAULT_CODE_ACCESS_DENIED),
            (exceptions.UserError("user oops"), RPC_FAULT_CODE_WARNING),
            (
                exceptions.RedirectWarning("redirect", 1, "Go"),
                RPC_FAULT_CODE_WARNING,
            ),
        ]
        for exception, expected_code in cases:
            fault = self._fault_from(xmlrpc_handle_exception_int(exception))
            self.assertEqual(fault.faultCode, expected_code)

    def test_int_fault_generic_exception_carries_traceback(self):
        try:
            raise ValueError("boom in rpc")
        except ValueError as error:
            fault = self._fault_from(xmlrpc_handle_exception_int(error))
        self.assertEqual(fault.faultCode, RPC_FAULT_CODE_APPLICATION_ERROR)
        self.assertIn("boom in rpc", fault.faultString)

    def test_string_fault_access_denied_is_bare(self):
        fault = self._fault_from(
            xmlrpc_handle_exception_string(exceptions.AccessDenied())
        )
        self.assertEqual(fault.faultCode, "AccessDenied")

    def test_string_fault_user_error_is_prefixed(self):
        fault = self._fault_from(
            xmlrpc_handle_exception_string(exceptions.UserError("user oops"))
        )
        self.assertTrue(str(fault.faultCode).startswith("warning -- UserError"))
        self.assertIn("user oops", str(fault.faultCode))


@tagged("post_install", "-at_install")
class TestFaultCarriesItsOwnException(TransactionCase):
    def _fault_from(self, payload):
        with self.assertRaises(xmlrpc.client.Fault) as capture:
            xmlrpc.client.loads(payload)
        return capture.exception

    def test_a_never_raised_exception_still_names_itself(self):
        for handler in (xmlrpc_handle_exception_int, xmlrpc_handle_exception_string):
            with self.subTest(handler=handler.__name__):
                fault = self._fault_from(handler(ValueError("boom, unraised")))
                rendered = f"{fault.faultCode}{fault.faultString}"
                self.assertIn("boom, unraised", rendered)
                self.assertNotIn("NoneType: None", rendered)

    def test_the_exception_passed_wins_over_the_one_in_flight(self):
        try:
            raise KeyError("the ambient one")
        except KeyError:
            fault = self._fault_from(
                xmlrpc_handle_exception_int(ValueError("the argument"))
            )
        self.assertIn("the argument", fault.faultString)
        self.assertNotIn("the ambient one", fault.faultString)

    def test_a_raised_exception_still_carries_its_stack(self):
        try:
            raise ValueError("raised for real")
        except ValueError as error:
            fault = self._fault_from(xmlrpc_handle_exception_int(error))
        self.assertIn("raised for real", fault.faultString)
        self.assertIn("Traceback (most recent call last)", fault.faultString)


@tagged("post_install", "-at_install")
class TestFaultHidesTheServerOutsideDevMode(TransactionCase):
    def _fault_from(self, payload):
        with self.assertRaises(xmlrpc.client.Fault) as capture:
            xmlrpc.client.loads(payload)
        return capture.exception

    @contextmanager
    def _serving_a_client(self):
        _request_stack.push(SimpleNamespace())
        try:
            with http_settings.override(dev_mode=()):
                yield
        finally:
            _request_stack.pop()

    def test_an_unexpected_error_carries_no_traceback_to_the_client(self):
        try:
            raise KeyError("nosuch")
        except KeyError as error:
            with self._serving_a_client():
                int_fault = self._fault_from(xmlrpc_handle_exception_int(error))
                str_fault = self._fault_from(xmlrpc_handle_exception_string(error))
        for fault in (int_fault, str_fault):
            rendered = f"{fault.faultCode}{fault.faultString}"
            self.assertNotIn("Traceback (most recent call last)", rendered)
            self.assertNotIn(".py", rendered)
            self.assertIn("nosuch", rendered)

    def test_an_infrastructure_error_is_masked(self):
        error = psycopg.OperationalError("UPDATE res_users SET password=...")
        with self._serving_a_client():
            fault = self._fault_from(xmlrpc_handle_exception_string(error))
        self.assertEqual(fault.faultCode, "Internal Server Error")
        self.assertNotIn("res_users", fault.faultString)


@tagged("post_install", "-at_install")
class TestMarkupMarshalling(TransactionCase):
    def test_markup_is_escaped_exactly_once(self):
        payload = dumps((Markup("<b>a &amp; b</b>"),))
        (value,), _method = xmlrpc.client.loads(payload)
        self.assertEqual(value, "<b>a &amp; b</b>")

    def test_the_dispatch_override_keeps_the_interpreter_fallbacks(self):
        class Arbitrary:
            def __init__(self):
                self.a = 1

        self.assertIn("struct", dumps((Arbitrary(),)))
        self.assertIn("struct", dumps((lazy(Arbitrary),)))
        payload = dumps((LangData({"id": 1, "code": "en_US"}),))
        (value,), _method = xmlrpc.client.loads(payload)
        self.assertEqual(value["code"], "en_US")
        with self.assertRaises(TypeError):
            xmlrpc.client.Marshaller(allow_none=False).dumps(
                (LangData({"id": 1, "code": "en_US"}),)
            )

    def test_the_conversion_is_what_makes_it_so(self):
        self.assertNotEqual(
            xmlrpc.client.escape(Markup("a & b")),
            xmlrpc.client.escape("a & b"),
        )
