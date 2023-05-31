import inspect
from typing import Callable, TypeVar, Any

import psycopg2

from odoo.exceptions import UserError
from odoo.tests import common


class TestFuzzer(common.TransactionCase):
    def setUp(self):
        super(TestFuzzer, self).setUp()
        self.fuzzer_model = self.env['test.fuzzer.model']
        self.fuzzer_record = self.create_canary_record()

        self.fuzzer_model_methods = get_public_functions(self.fuzzer_model)
        self.default_args = {
            "domain": [],
            "fields": ["n"],
            "groupby": "n",
            "field_names": ["n"],
            "data": [[]],
            "operation": "read",
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

            injections = get_injections_for_parameter(parameter)
            if injections is None:
                print(f"\tUnfuzzed parameter {parameter}")
                continue

            for injection in injections:
                fuzzed_args = args.copy()
                fuzzed_args[parameter] = injection

                print(f"\t{parameter}=`{injection}`... ", end="")

                throws_error = False
                caught_during_validation = False

                try:
                    function(self.fuzzer_record, **fuzzed_args)
                except (UserError, ValueError, KeyError) as e:
                    throws_error = True
                    caught_during_validation = True

                    print()
                    print(f"\t\t {e.__class__} {e}... ", end="")

                except psycopg2.Error as e:
                    # TODO: Maybe capture more precise errors.
                    throws_error = True
                    caught_during_validation = False

                    print()
                    print(f"\t\t {e.__class__} {e}... ", end="")

                if self.did_injection_succeed():
                    print("FAIL")
                elif throws_error and caught_during_validation:
                    print("OK")
                elif throws_error and not caught_during_validation:
                    print("ERROR IN DB")
                elif not throws_error:
                    print("NO ERROR")
                else:
                    assert False

    def did_injection_succeed(self):
        count = self.fuzzer_model.search_count([])
        if count == 0:
            # Put back the removed canary record
            self.fuzzer_record = self.create_canary_record()
            return True
        return False


delete_from_table = "delete from test_fuzzer_model"


def get_injections_for_parameter(parameter: str) -> list[Any] | None:
    if parameter == "domain":
        return create_domain_injections("n")
    if parameter == "order":
        return create_order_injections("n")
    if parameter == "fields":
        return create_fields_injections("n")
    if parameter == "field_names":
        return create_fields_injections("n")
    if parameter == "groupby":
        return create_groupby_injections("n")
    if parameter == "vals":
        return create_vals_injections("n")
    if parameter == "vals_list":
        return create_vals_list_injections("n")
    return None


def create_quoted_field_name(field_name: str) -> list[str]:
    return [
        f"""{field_name}""",
        f"""{field_name}\"""",
        f"""{field_name}'""",
        f"""{field_name}\\""",
    ]


def create_where_injections(field_name: str) -> list[list[tuple[str, str, Any]]]:
    return [
        [(fr"""{field_name} = "1337"); {delete_from_table} -- -""", "=", "1337")]
        for field_name in create_quoted_field_name(field_name)
    ]


def create_column_name_injections(field_name: str, right_parenthesis=False) -> list[str]:
    return [
        f"""{field_name}{")" if right_parenthesis else ""}; {delete_from_table} -- -"""
        for field_name in create_quoted_field_name(field_name)
    ]


def create_domain_injections(field_name: str) -> list[list[tuple[str, str, Any]]]:
    return create_where_injections(field_name)


def create_order_injections(field_name: str) -> list[str]:
    return create_column_name_injections(field_name)


def create_fields_injections(field_name: str) -> list[list[str]]:
    return [[injection] for injection in create_column_name_injections(field_name)]


def create_groupby_injections(field_name: str) -> list[str]:
    return create_column_name_injections(field_name)


def create_vals_injections(field_name: str) -> list[dict[str, int]]:
    return [{injection: "1337"} for injection in create_column_name_injections(field_name)]


def create_vals_list_injections(field_name: str) -> list[list[dict[str, str]]]:
    field_name_injections = [
        [{field_name: "1337"}]
        for field_name in create_column_name_injections(field_name)
    ]

    # TODO: Absence of an error should be OK.
    value_injections = [
        [{"n": value}]
        for value in create_column_name_injections(field_name, right_parenthesis=True)
    ]

    return field_name_injections + value_injections


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
