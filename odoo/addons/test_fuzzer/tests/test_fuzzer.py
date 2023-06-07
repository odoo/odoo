import inspect
import logging
from typing import Type

import psycopg2

from odoo import registry, tools
from odoo.addons.test_fuzzer.injection import *
from odoo.exceptions import UserError
from odoo.models import BaseModel
from odoo.tests import common

_logger = logging.getLogger(__name__)


class TestFuzzer(common.TransactionCase):
    def setUp(self):
        super(TestFuzzer, self).setUp()

        # We can't use the environment cursor because we need to manually commit and roll back transactions.
        self.cr = registry(self.env.cr.dbname).cursor()
        self.fuzzer_env = self.env(cr=self.cr)

        self.fuzzer_model = self.fuzzer_env['test.fuzzer.model']
        self.fuzzer_model_methods = patch_function_list(get_public_functions(self.fuzzer_model.__class__))
        self.fuzzer_record = self.create_canary_record()

        self.injections: dict[str, [Injection]] = {
            "ids": wrap_payload(construct_value_injections("1337", with_closing_parenthesis=True),
                                lambda payload: [payload]) +
                   wrap_payload(construct_injections(create_id_payloads(), expect_error=False),
                                lambda payload: [payload]),
            "limit": construct_value_injections("1"),
            "offset": construct_value_injections("0"),
            "domain": construct_where_clause_injections("n"),
            "order": construct_value_injections("n"),
            "fields": wrap_payload(construct_value_injections("n"), lambda payload: [payload]),
            "fnames": wrap_payload(construct_value_injections("n"), lambda payload: [payload]),
            "field_names": wrap_payload(construct_value_injections("n"), lambda payload: [payload]),
            "field_name": construct_value_injections("n"),
            "fields_list": wrap_payload(construct_value_injections("n"), lambda payload: [payload]),
            "fields_to_export": wrap_payload(construct_value_injections("n"), lambda payload: [payload]),
            "name": construct_value_injections("n"),
            "allfields": wrap_payload(construct_value_injections("n"), lambda payload: [payload]),
            "attributes": wrap_payload(construct_value_injections("type"), lambda payload: [payload]),
            "groupby": construct_value_injections("n"),
            "orderby": construct_value_injections("n"),
            "values": wrap_payload(construct_value_injections("n"), lambda payload: {payload: "1337"}),
            "vals": wrap_payload(construct_value_injections("n"), lambda payload: {payload: "1337"}),
            "vals_list": wrap_payload(construct_value_injections("n"), lambda payload: [{payload: "1337"}]) +
                         wrap_payload(construct_value_injections(
                             "n", expect_error=False, with_closing_parenthesis=True),
                             lambda payload: [{"n": payload}]),
        }

        self.validation_errors = (
            UserError,
            ValueError,
            KeyError,
            TypeError,
        )
        self.sql_errors = (
            psycopg2.errors.InvalidTextRepresentation,
            psycopg2.errors.InvalidRowCountInLimitClause,
            psycopg2.errors.NumericValueOutOfRange,
        )

    def test_fuzzer(self):
        for method, signature in self.fuzzer_model_methods:
            self.fuzz_function(method, signature)

    def fuzz_function(self, function: Callable, signature: inspect.Signature):
        """Iterates over all parameters of a function and fuzzes them."""
        for parameter in signature.parameters:
            if parameter == "self":
                continue

            self.fuzz_function_parameter(parameter, function, signature)

    def fuzz_function_parameter(self, parameter: str, function: Callable, signature: inspect.Signature):
        """Repeatedly calls a method by trying various SQL injections on the same parameter."""
        if parameter not in self.injections:
            _logger.debug("Unfuzzed parameter `%s` on method `%s`", parameter, function.__name__)
            return

        for injection in self.injections[parameter]:
            _logger.debug("Fuzzing `%s` with %s=%s", function.__name__, parameter, injection.payload)

            # If the function has multiple positional arguments, all of them must be assigned to be able to call it.
            # We assign a default value to all of them.
            args: dict[str, Any] = {
                name: value for name, value in self.get_default_args().items()
                if name in signature.parameters and signature.parameters[name].default == signature.empty}

            # Replace the argument's default value with an injection.
            args[parameter] = injection.payload

            # The reason we're not just calling the function blindly is that TypeError can actually be thrown in some
            # cases during injections, and we wouldn't have a way to differentiate between a failed injection and a
            # function call whose arguments are missing. Therefore, we explicitly test if the function can be called
            # without errors before actually calling it.
            try:
                bound_arguments: inspect.BoundArguments = signature.bind(**args)
            except TypeError:
                _logger.debug("Function `%s` couldn't be called because "
                              "some required parameters don't have a default value."
                              "You should populate the default args dictionary.", function.__name__)
                return

            savepoint = self.cr.savepoint()

            try:
                with tools.mute_logger('odoo.sql_db'):
                    function(*bound_arguments.args, **bound_arguments.kwargs)
                self.cr.commit()

                self.assertFalse(self.did_injection_succeed(),
                                 f"SQL injection successful on method `{function.__name__}` "
                                 f"with {parameter}={injection.payload}")

            except self.validation_errors as e:
                self.assert_error_expected(e, injection, function)

            except self.sql_errors as e:
                savepoint.close()

                self.assert_error_expected(e, injection, function)
                self.assertTrue(was_execute_method_called_correctly(),
                                f"Method `{function.__name__}` is susceptible to SQL injection "
                                f"with {parameter}={injection.payload}")

    def get_default_args(self):
        """
        Functions are fuzzed one parameter at a time.
        If a function has multiple positional arguments, the non-fuzzed ones are assigned a value from this dictionary.
        """
        return {
            "self": self.fuzzer_record,
            "domain": [],
            "fields": ["n"],
            "groupby": "n",
            "field_names": ["n"],
            "data": [[]],
            "operation": "read",
            "values": {"n": "1337"},
            "field_name": "n",
            "field_onchange": {"n"},
            "translations": {},
        }

    def did_injection_succeed(self) -> bool:
        """
        Returns True if the canary record was erased due to an SQL injection.
        The canary is put back for the next series of injections.
        """
        count = self.fuzzer_model.search_count([])
        if count == 0:
            self.fuzzer_record = self.create_canary_record()
            self.cr.commit()
            return True
        return False

    def create_canary_record(self):
        return self.fuzzer_model.create({'n': '1337'})[0]

    def assert_error_expected(self, e: Exception, injection: Injection, function: Callable):
        """Something's wrong if an exception is thrown when the injection is not supposed to trigger an error."""
        self.assertTrue(injection.expect_error,
                        f"Method {function.__name__} threw an unexpected error during fuzzing "
                        f"with payload {injection}: {e}")


def get_public_functions(cls: Type) -> list[tuple[Callable, inspect.Signature]]:
    functions = []

    for attribute_name in dir(cls):
        attribute_name: str
        if attribute_name.startswith("_"):
            continue

        function = getattr(cls, attribute_name)
        if not inspect.isfunction(function):
            continue

        signature: inspect.Signature = inspect.signature(function)

        functions.append((function, signature))

    return functions


def was_execute_method_called_correctly() -> bool:
    """
    Returns True if the `execute` method of the cursor was called with 2 arguments: query and params.
    No SQL injection should be possible if this is the case.
    This function must be called only inside an except block.
    """

    def is_execute_method(frame: inspect.FrameInfo):
        module_name = inspect.getmodule(frame[0]).__name__
        return module_name == "odoo.sql_db" and frame.function == "execute"

    execute_method_frame = next(filter(is_execute_method, inspect.trace()), None)
    if execute_method_frame is None:
        return False

    method_locals = inspect.getargvalues(execute_method_frame[0]).locals
    if "query" in method_locals and "params" in method_locals:
        return method_locals["params"] is not None

    return False


def patch_function_list(functions: list[tuple[Callable, inspect.Signature]]) \
        -> list[tuple[Callable, inspect.Signature]]:
    """
    Some methods like `browse` are not worth testing on their own because all they do is set some fields without
    executing an SQL query.
    What's interesting, however, is to combine them with other methods that execute queries.
    """

    def browse_and_read(self: BaseModel, ids):
        m = self.browse(ids)
        return m.read()

    exclude_functions = [
        BaseModel.browse,
    ]

    include_functions = [
        browse_and_read,
    ]

    filtered_functions = list(filter(lambda f: f[0] not in exclude_functions, functions))
    filtered_functions.extend([(f, inspect.signature(f)) for f in include_functions])
    return filtered_functions
