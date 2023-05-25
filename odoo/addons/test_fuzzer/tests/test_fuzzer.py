from functools import partial
from typing import Callable

from odoo.tests import common


class TestFuzzer(common.TransactionCase):
    def setUp(self):
        super(TestFuzzer, self).setUp()
        self.fuzzer_model = self.env['test.fuzzer.model']
        self.create_canary_record()

    def create_canary_record(self):
        self.fuzzer_model.create({'n': 1337})

    def test_fuzz_domain(self):
        self.fuzz_domain([
            self.fuzzer_model.search,
        ])

    def test_fuzz_order(self):
        self.fuzz_order([
            partial(self.fuzzer_model.search, domain=[])
        ])

    def fuzz_domain(self, functions: list[Callable]):
        injections = inject_domain("n")

        for function in functions:
            for injection in injections:
                try:
                    function(domain=[(injection, "=", 1337)])
                except:
                    pass
                if self.did_injection_succeed():
                    print(injection)

    def fuzz_order(self, functions: list[Callable]):
        injections = inject_order("n")

        for function in functions:
            for injection in injections:
                try:
                    function(order=injection)
                except:
                    pass
                if self.did_injection_succeed():
                    print(injection)

    def did_injection_succeed(self):
        count = self.fuzzer_model.search_count([])
        if count == 0:
            # Put back the removed canary record
            self.create_canary_record()
            return True
        return False


delete_from_table = "delete from test_fuzzer_model"


def inject_domain(field_name: str) -> list[str]:
    return [
        f"""{field_name}" = 1337); {delete_from_table} --""",
        f"""{field_name}' = 1337); {delete_from_table} --""",
    ]


def inject_order(field_name: str) -> list[str]:
    return [
        f"""{field_name}"; {delete_from_table} --""",
    ]

# search
# read
# write
# browse
# create
# web read group
# search read
