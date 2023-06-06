import dataclasses
from dataclasses import dataclass
from math import inf, nan
from typing import Any, Callable


@dataclass
class Injection:
    payload: Any
    expect_error: bool


def construct_where_clause_injections(payload: Any, expect_error=True) -> list[Injection]:
    return [construct_where_clause_injection(payload, expect_error)
            for payload in create_quoted_payloads(payload)]


def construct_field_reference_injections(payload: Any, expect_error=True,
                                         with_closing_parenthesis=False) -> list[Injection]:
    return [construct_field_reference_injection(payload, expect_error, with_closing_parenthesis)
            for payload in create_quoted_payloads(payload)]


def construct_injections(payloads: list[Any], expect_error=True) -> list[Injection]:
    return [Injection(payload, expect_error) for payload in payloads]


def wrap_payload(injections: list[Injection], f: Callable[[Any], Any]) -> list[Injection]:
    return [dataclasses.replace(injection, payload=f(injection.payload)) for injection in injections]


def construct_where_clause_injection(payload: Any, expect_error: bool) -> Injection:
    payload = [(fr"""{payload} = "1337"); {delete_from_table} -- -""", "=", "1337")]
    return Injection(payload, expect_error)


def construct_field_reference_injection(payload: Any, expect_error: bool,
                                        with_closing_parenthesis: bool) -> Injection:
    payload = f"""{payload}{")" if with_closing_parenthesis else ""}; {delete_from_table} -- -"""
    return Injection(payload, expect_error)


def create_quoted_payloads(payload: str) -> list[str]:
    return [
        f"""{payload}""",
        f"""{payload}\"""",
        f"""{payload}'""",
        f"""{payload}\\""",
    ]


def create_id_payloads() -> list[int]:
    return [
        -1,
        0,
        2 ** 64,
        inf,
        -inf,
        nan,
    ]


def create_positive_number_payloads() -> list[Any]:
    return [
        2 ** 64,
        inf,
        nan,
    ]


delete_from_table = "delete from test_fuzzer_model"
