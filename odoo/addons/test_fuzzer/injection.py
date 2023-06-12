import functools
import inspect
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Generator


@dataclass()
class InjectionReport:
    function: Callable
    arguments: inspect.BoundArguments
    error: Exception | None
    is_injection_successful: bool

    def __str__(self) -> str:
        args = ", ".join([f"{name}={value}" for name, value in self.arguments.arguments.items()])
        s = f"{self.function.__name__}({args})\n\n"
        if self.is_injection_successful:
            s += "Injection successful !"
        elif self.error:
            s += "".join(traceback.format_exception(self.error))
        else:
            s += "No errors."
        return s


def with_dot(payload: Any) -> Generator[str, None, None]:
    yield payload
    yield f"{payload}."


def with_quotes(payload: Any) -> Generator[str, None, None]:
    yield payload
    yield f"{payload}\""
    yield f"{payload}\'"


def with_parenthesis(payload: Any) -> Generator[str, None, None]:
    yield payload
    yield f"{payload})"


def with_different_types(payload: Any) -> Generator[Any, None, None]:
    yield payload
    yield [payload]
    yield {payload: "1337"}
    yield {"n": payload}
    yield [(payload, "ilike", "1337")]


def with_delete_table(payload: Any) -> Generator[str, None, None]:
    yield f"{payload}; {delete_from_table} -- -"


PayloadGenerator = Callable[[Any], Generator[str, None, None]]


def pipe(a: PayloadGenerator, b: PayloadGenerator) -> PayloadGenerator:
    def f(value: Any) -> Generator[str, None, None]:
        for item in a(value):
            yield from b(item)

    return f


def compose(*functions) -> PayloadGenerator:
    return functools.reduce(lambda a, b: pipe(a, b), functions)


payload_generator: PayloadGenerator = compose(
    with_dot,
    with_quotes,
    with_parenthesis,
    with_delete_table,
    with_different_types,
)

delete_from_table = "delete from test_fuzzer_model"
