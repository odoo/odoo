import inspect
from typing import Callable, Dict, TypeVar, List, Any

from odoo.exceptions import UserError
from odoo.tests import common


class TestFuzzer(common.TransactionCase):
    def setUp(self):
        super(TestFuzzer, self).setUp()
        self.fuzzer_model = self.env['test.fuzzer.model']
        self.fuzzer_model_methods = get_public_methods(self.fuzzer_model)
        self.fuzzer_model.browse()
        self.create_canary_record()

    def create_canary_record(self):
        self.fuzzer_model.create({'n': 1337})

    def test_fuzz_domain(self):
        methods_with_domain = filter_dict(lambda signature, _: "domain" in signature.parameters,
                                          self.fuzzer_model_methods)

        self.fuzz_functions(
            functions=methods_with_domain,
            default_args={
                "fields": ["n"],
                "groupby": "n",
                "field_names": ["n"],
            },
            fuzzed_parameter="domain",
            injections=create_domain_injections("n"),
        )

    def test_fuzz_order(self):
        methods_with_order = filter_dict(lambda signature, _: "order" in signature.parameters,
                                         self.fuzzer_model_methods)

        self.fuzz_functions(
            functions=methods_with_order,
            default_args={
                "domain": [],
                "fields": ["n"],
                "groupby": "n",
                "field_names": ["n"],
            },
            fuzzed_parameter="order",
            injections=create_order_injections("n"),
        )

    def test_fuzz_fields(self):
        methods_with_order = filter_dict(lambda signature, _: "fields" in signature.parameters,
                                         self.fuzzer_model_methods)

        self.fuzz_functions(
            functions=methods_with_order,
            default_args={
                "domain": [],
                "groupby": "n",
                "field_names": ["n"],
                "data": [[]],
            },
            fuzzed_parameter="fields",
            injections=create_fields_injections("n"),
        )

    def test_fuzz_groupby(self):
        methods_with_order = filter_dict(lambda signature, _: "groupby" in signature.parameters,
                                         self.fuzzer_model_methods)

        self.fuzz_functions(
            functions=methods_with_order,
            default_args={
                "domain": [],
                "field_names": ["n"],
                "fields": ["n"],
                "data": [[]],
            },
            fuzzed_parameter="groupby",
            injections=create_groupby_injections("n"),
        )

    def fuzz_functions(self,
                       functions: Dict[inspect.Signature, Callable],
                       # Some functions might have required parameters other than the fuzzed one.
                       default_args: Dict[str, Any],
                       fuzzed_parameter: str,
                       injections: List[Any]):
        for signature, function in functions.items():
            # Remove superfluous arguments and only populate required parameters.
            args = {name: value for name, value in default_args.items() if
                    name in signature.parameters and signature.parameters[name].default == signature.empty}

            print(f"Testing {function.__name__}...")
            for injection in injections:
                print(f"    {fuzzed_parameter}=`{injection}`... ", end="")

                fuzzed_args = args.copy()
                fuzzed_args[fuzzed_parameter] = injection

                try:
                    function(**fuzzed_args)
                except (UserError, ValueError, KeyError):
                    pass

                if self.did_injection_succeed():
                    print("FAIL")
                else:
                    print("OK")

    def did_injection_succeed(self):
        count = self.fuzzer_model.search_count([])
        if count == 0:
            # Put back the removed canary record
            self.create_canary_record()
            return True
        return False


delete_from_table = "delete from test_fuzzer_model"


def create_domain_injections(field_name: str) -> list[list[tuple]]:
    return [
        [(fr"""{field_name}" = 1337); {delete_from_table} --""", "=", 1337)],
        [(fr"""{field_name}' = 1337); {delete_from_table} --""", "=", 1337)],
    ]


def create_order_injections(field_name: str) -> list[str]:
    return [
        f"""{field_name}"; {delete_from_table} --""",
    ]


def create_fields_injections(field_name: str) -> list[list[str]]:
    return [
        [f"""{field_name}"; {delete_from_table} --"""],
    ]


def create_groupby_injections(field_name: str) -> list[str]:
    return [
        f"""{field_name}"; {delete_from_table} --""",
    ]


def get_public_methods(obj: object) -> Dict[inspect.Signature, Callable]:
    methods = {}

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
        method = attribute

        signature: inspect.Signature = inspect.signature(method)
        methods[signature] = method

    return methods


T = TypeVar('T')
U = TypeVar('U')


def filter_dict(function: Callable[[T, U], bool], d: Dict[T, U]) -> Dict[T, U]:
    return {key: value for key, value in d.items() if function(key, value)}

# search
# read
# write
# browse
# create
# web read group
# search read
