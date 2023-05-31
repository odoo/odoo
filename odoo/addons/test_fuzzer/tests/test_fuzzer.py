import inspect
from typing import TypeVar

import psycopg2

from odoo.addons.test_fuzzer.injection import *
from odoo.exceptions import UserError
from odoo.tests import common


class TestFuzzer(common.TransactionCase):
    def setUp(self):
        super(TestFuzzer, self).setUp()
        self.fuzzer_model = self.env['test.fuzzer.model']
        self.fuzzer_model_methods = get_public_functions(self.fuzzer_model)
        self.fuzzer_record = self.create_canary_record()

        self.default_args = {
            "domain": [],
            "fields": ["n"],
            "groupby": "n",
            "field_names": ["n"],
            "data": [[]],
            "operation": "read",
        }

        self.injections: dict[str, [Injection]] = {
            "domain": construct_where_clause_injections("n"),
            "order": construct_field_reference_injections("n"),
            "fields": wrap_payload(construct_field_reference_injections("n"), lambda payload: [payload]),
            "field_names": wrap_payload(construct_field_reference_injections("n"), lambda payload: [payload]),
            "groupby": construct_field_reference_injections("n"),
            "vals": wrap_payload(construct_field_reference_injections("n"), lambda payload: {payload: "1337"}),
            "vals_list": wrap_payload(construct_field_reference_injections("n"), lambda payload: [{payload: "1337"}]) +
                         wrap_payload(construct_field_reference_injections(
                             "n", expect_error=True, with_closing_parenthesis=True),
                             lambda payload: [{"n": payload}]
                         ),
        }

    def create_canary_record(self):
        return self.fuzzer_model.create({'n': '1337'})[0]

    def test_fuzzer(self):
        for signature, method in self.fuzzer_model_methods:
            self.fuzz_function(signature, method)

    def fuzz_function(self, signature: inspect.Signature, function: Callable):
        # Don't test functions that don't have any parameters other than self.
        if len(signature.parameters) < 2:
            return

        print(f"Testing: {function.__name__}")

        # Remove superfluous arguments and only populate required parameters.
        args = {name: value for name, value in self.default_args.items() if
                name in signature.parameters and signature.parameters[name].default == signature.empty}

        for parameter in signature.parameters:
            if parameter == "self":
                continue

            injections = self.injections.get(parameter)
            if injections is None:
                print(f"\tUnfuzzed parameter {parameter}")
                continue

            for injection in injections:
                fuzzed_args = args.copy()
                fuzzed_args[parameter] = injection.payload

                print(f"\t{parameter}=`{injection.payload}`... ", end="")

                throws_exception = False
                caught_during_validation = False

                try:
                    function(self.fuzzer_record, **fuzzed_args)
                except (UserError, ValueError, KeyError) as e:
                    throws_exception = True
                    caught_during_validation = True

                    print()
                    print(f"\t\t {e.__class__} {e}... ", end="")

                except psycopg2.Error as e:
                    # TODO: Maybe capture more precise errors.
                    throws_exception = True
                    caught_during_validation = False

                    print()
                    print(f"\t\t {e.__class__} {e}... ", end="")

                if self.did_injection_succeed():
                    print("FAIL")
                elif injection.expect_error and throws_exception and caught_during_validation:
                    print("OK")
                elif injection.expect_error and throws_exception and not caught_during_validation:
                    print("ERROR IN DB")
                elif injection.expect_error and not throws_exception:
                    print("NO ERRORS")
                else:
                    assert not injection.expect_error and not throws_exception
                    print("OK")

    def did_injection_succeed(self):
        count = self.fuzzer_model.search_count([])
        if count == 0:
            # Put back the removed canary record
            self.fuzzer_record = self.create_canary_record()
            return True
        return False


def get_public_functions(obj: object) -> list[(inspect.Signature, Callable)]:
    functions = []

    for attribute_name in dir(obj):
        attribute_name: str
        if attribute_name.startswith("_"):
            continue

        try:
            attribute = getattr(obj, attribute_name)
        except:
            # getattr() triggers some Odoo defined method that throws unexpected exceptions.
            continue

        if not inspect.ismethod(attribute):
            continue

        function = attribute.__func__
        signature: inspect.Signature = inspect.signature(function)
        functions.append((signature, function))

    return functions


T = TypeVar('T')
U = TypeVar('U')


def filter_dict(function: Callable[[T, U], bool], d: dict[T, U]) -> dict[T, U]:
    return {key: value for key, value in d.items() if function(key, value)}

# search x
# read x
# write x
# browse /
# create
# read group x
# search read x
