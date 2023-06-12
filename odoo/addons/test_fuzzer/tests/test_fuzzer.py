import logging
from typing import Type

import psycopg2

from odoo import registry, tools
from odoo.addons.test_fuzzer.injection import *
from odoo.addons.test_fuzzer.models import FuzzerModel
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

        self.injection_reports: list[InjectionReport] = []

        # Some parameters take other values than model field names.
        # We try to be smart about it by choosing a value that is likely to be accepted by the function.
        self.seeds = {
            "ids": "1337",
            "limit": "1",
            "offset": "0",
            "attributes": "type",
        }

        self.validation_errors = (
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            IndexError,
            AssertionError,
            UserError,
        )
        self.sql_errors = (
            psycopg2.errors.SyntaxError,
            psycopg2.errors.UndefinedColumn,
            psycopg2.errors.InvalidTextRepresentation,
            psycopg2.errors.UndefinedFunction,
            psycopg2.errors.DatatypeMismatch,
            psycopg2.errors.ProgrammingError,  # Must be last because it's a superclass.
        )

    def test_fuzzer(self):
        for method, signature in self.fuzzer_model_methods:
            self.fuzz_function(method, signature)

    def fuzz_function(self, function: Callable, signature: inspect.Signature):
        """Iterates over all parameters of a function and fuzzes them."""
        for model_field in ["char", "char_translate", "text", "integer", "selection", "boolean", "float", "html",
                            "date", "datetime", "binary", "many2one", "one2many"]:
            for parameter in signature.parameters:
                if parameter == "self":
                    continue

                for injection in payload_generator(self.seeds.get(parameter, model_field)):
                    self.fuzz_function_parameter(parameter, injection, function, signature)

    def fuzz_function_parameter(self, parameter: str, injection: Any, function: Callable, signature: inspect.Signature):
        """Fuzzes a single parameter with a single injection."""
        _logger.debug("Fuzzing `%s` with %s=%s", function.__name__, parameter, injection)

        # If the function has multiple positional arguments, all of them must be assigned to be able to call it.
        # We assign a default value to all of them.
        args: dict[str, Any] = {
            name: value for name, value in self.get_default_args().items()
            if name in signature.parameters and signature.parameters[name].default == signature.empty}

        # Replace the argument's default value with an injection.
        args[parameter] = injection

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

        error = None
        is_injection_successful = False

        try:
            with tools.mute_logger("odoo.sql_db", "odoo.osv.expression", "odoo.tools.cache"):
                function(*bound_arguments.args, **bound_arguments.kwargs)
            self.cr.commit()

            is_injection_successful = self.did_injection_succeed()

        except self.validation_errors as e:
            error = e

        except self.sql_errors as e:
            savepoint.close()
            error = e

        finally:
            report = InjectionReport(function, bound_arguments, error, is_injection_successful)
            self.injection_reports.append(report)

    def get_default_args(self):
        """
        Functions are fuzzed one parameter at a time.
        If a function has multiple positional arguments, the non-fuzzed ones are assigned a value from this dictionary.
        """
        return {
            "self": self.fuzzer_record,
            "domain": [],
            "fields": ["char"],
            "groupby": "char",
            "field_names": ["char"],
            "data": [[]],
            "operation": "read",
            "values": {"char": "1337"},
            "field_name": "char",
            "field_onchange": {"char"},
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

        elif count >= 1000:
            # Reinitialize the table occasionally because having too many records in it slows down the fuzzing.
            self.clear_fuzzer_table()
            self.fuzzer_record = self.create_canary_record()
            self.cr.commit()

        return False

    def create_canary_record(self) -> FuzzerModel:
        return self.fuzzer_model.create({
            "char": "1337",
            "char_translate": "1337",
        })[0]

    def tearDown(self):
        # noinspection SqlWithoutWhere
        self.clear_fuzzer_table()
        self.cr.close()
        self.create_test_report()
        super().tearDown()

    def clear_fuzzer_table(self):
        # noinspection SqlWithoutWhere
        self.cr.execute("delete from test_fuzzer_model")
        self.cr.commit()

    def create_test_report(self):
        successful_injections = list(filter(lambda report: report.is_injection_successful, self.injection_reports))
        unsafe_injections = list(
            filter(lambda report: report.error.__class__ in self.sql_errors, self.injection_reports))

        def construct_report_message() -> str:
            msg = "\n\n".join(map(str, successful_injections + unsafe_injections))
            msg += (f"\n\nPerformed {len(self.injection_reports)} injections: "
                    f"{len(successful_injections)} were successful, "
                    f"{len(unsafe_injections)} were unsafe.")
            return msg

        self.assertTrue(not successful_injections and not unsafe_injections,
                        construct_report_message())


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
