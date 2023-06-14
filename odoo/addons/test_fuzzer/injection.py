import functools
import inspect
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Generator


@dataclass()
class InjectionReport:
    function: Callable
    arguments: inspect.BoundArguments
    query: str | None
    error: Exception | None
    is_injection_successful: bool

    def __str__(self) -> str:
        s = f"{format_bound_arguments(self.function, self.arguments)}\n\n"
        if self.is_injection_successful:
            s += f"Injection successful !\n"
        elif self.error:
            s += "".join(traceback.format_exception(self.error))
        else:
            s += "No errors.\n"

        if self.query:
            s += f"Query: {self.query}"

        return s


def format_bound_arguments(function: Callable, bound_arguments: inspect.BoundArguments) -> str:
    args = ", ".join([f"{name}={value}" for name, value in bound_arguments.arguments.items()])
    return f"{function.__name__}({args})"


def with_dot(payload: Any) -> Generator[str, None, None]:
    yield f"{payload}"
    yield f"{payload}."


def with_quotes(payload: Any) -> Generator[str, None, None]:
    yield f"{payload}"
    yield f"{payload}\""
    yield f"{payload}\'"


def with_parenthesis(payload: Any) -> Generator[str, None, None]:
    yield f"{payload}"
    yield f"{payload})"


def with_delete_table(payload: Any) -> Generator[str, None, None]:
    # Try to cause a SyntaxError without injecting anything.
    yield f"{payload}"
    # We're doing a `select` at the end because we want the query to stay fetchable.
    yield f"{payload}; {delete_from_table}; select * from {table} -- -"


def with_different_types(payload: Any) -> Generator[Any, None, None]:
    yield payload
    yield [payload]
    yield {payload: "1337"}
    yield {"char": payload}
    yield [(payload, "ilike", "1337")]


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

table = "test_fuzzer_model"
# noinspection SqlWithoutWhere
delete_from_table = f"delete from {table}"
