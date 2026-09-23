import ast
import tokenize
from tokenize import COMMENT, NAME, OP, STRING, generate_tokens
from typing import IO, TYPE_CHECKING, NamedTuple

from babel.util import parse_encoding, parse_future_flags

from ._frames import (
    Frame,
    close_keyword_frame,
    handle_line_comment,
    open_call_frame,
)


class _NameToken(NamedTuple):
    lineno: int
    value: str


type _SimpleKeyword = tuple[int | tuple[int, int] | tuple[int, str], ...] | None
type _Keyword = dict[int | None, _SimpleKeyword] | _SimpleKeyword
type _ExtractionResult = tuple[int, str, str | tuple[str, ...], list[str]]

if TYPE_CHECKING:
    from collections.abc import Collection, Generator, Mapping
    from typing import TypedDict

    class _PyOptions(TypedDict, total=False):
        encoding: str


FSTRING_START = tokenize.FSTRING_START if hasattr(tokenize, "FSTRING_START") else None
FSTRING_MIDDLE = (
    tokenize.FSTRING_MIDDLE if hasattr(tokenize, "FSTRING_MIDDLE") else None
)
FSTRING_END = tokenize.FSTRING_END if hasattr(tokenize, "FSTRING_END") else None


def _parse_python_string(value: str, encoding: str, future_flags: int) -> str | None:
    code = compile(
        f"# coding={encoding!s}\n{value}",
        "<string>",
        "eval",
        ast.PyCF_ONLY_AST | future_flags,
    )
    if isinstance(code, ast.Expression):
        body = code.body
        if isinstance(body, ast.Constant):
            return body.value if isinstance(body.value, str) else None
        if isinstance(body, ast.JoinedStr):
            parts = [
                n.value
                for n in body.values
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
            ]
            if len(parts) == len(body.values):
                return "".join(parts)
    return None


def _collect_keyword_message(
    token: int,
    value: str,
    lineno: int,
    function_stack: list[Frame],
    message_buffer: list[str],
    current_fstring_start: str | None,
    encoding: str,
    future_flags: int,
) -> str | None:
    if token == STRING:
        string_value = _parse_python_string(value, encoding, future_flags)
        if not function_stack[-1]["message_lineno"]:
            function_stack[-1]["message_lineno"] = lineno
        if string_value is not None:
            message_buffer.append(string_value)
    elif token == FSTRING_START:
        return value
    elif token == FSTRING_MIDDLE:
        if current_fstring_start is not None:
            return current_fstring_start + value
    elif token == FSTRING_END:
        if current_fstring_start is not None:
            string_value = _parse_python_string(
                current_fstring_start + value, encoding, future_flags
            )
            if string_value is not None:
                message_buffer.append(string_value)
    elif token == OP and value == ",":
        if message_buffer:
            function_stack[-1]["messages"].append("".join(message_buffer))
            message_buffer.clear()
        else:
            function_stack[-1]["messages"].append(None)
    return current_fstring_start


def _after_token(
    token: int,
    value: str,
    lineno: int,
    function_stack: list[Frame],
    last_name: str | None,
    current_fstring_start: str | None,
) -> tuple[str | None, str | None]:
    if token == NAME:
        last_name = value
        if function_stack and not function_stack[-1]["message_lineno"]:
            function_stack[-1]["message_lineno"] = lineno
    else:
        last_name = None
    if current_fstring_start is not None and token not in {
        FSTRING_START,
        FSTRING_MIDDLE,
    }:
        current_fstring_start = None
    return last_name, current_fstring_start


def extract_python(
    fileobj: IO[bytes],
    keywords: Mapping[str, _Keyword],
    comment_tags: Collection[str],
    options: _PyOptions,
) -> Generator[_ExtractionResult]:
    encoding = parse_encoding(fileobj) or options.get("encoding", "utf-8")
    future_flags = parse_future_flags(fileobj, encoding)

    def next_line():
        return fileobj.readline().decode(encoding)

    tokens = generate_tokens(next_line)

    function_stack: list[Frame] = []
    last_name = current_fstring_start = None
    in_def = in_translator_comments = False
    translator_comments: list[tuple[int, str]] = []
    message_buffer: list[str] = []

    for token, value, (lineno, _), _, _ in tokens:
        if token == NAME and value in ("def", "class"):
            in_def = True
            continue

        if in_def and token == OP and value in ("(", ":"):
            in_def = False
            continue

        if token == OP and value == "(" and last_name:
            translator_comments = open_call_frame(
                function_stack,
                translator_comments,
                message_buffer,
                _NameToken(lineno, last_name),
                function_lineno=lineno,
                message_lineno=None,
                messages=[],
            )
            last_name = None

        elif token == COMMENT:
            in_translator_comments, skip = handle_line_comment(
                value[1:].strip(),
                lineno,
                comment_tags,
                in_translator_comments,
                translator_comments,
            )
            if skip:
                continue

        elif function_stack and function_stack[-1]["function_name"] in keywords:
            if token == OP and value == ")":
                result = close_keyword_frame(function_stack, message_buffer)
                lineno = result[0]
                yield result

            else:
                current_fstring_start = _collect_keyword_message(
                    token,
                    value,
                    lineno,
                    function_stack,
                    message_buffer,
                    current_fstring_start,
                    encoding,
                    future_flags,
                )

        elif function_stack and token == OP and value == ")":
            function_stack.pop()

        if in_translator_comments and translator_comments[-1][0] < lineno:
            in_translator_comments = False

        last_name, current_fstring_start = _after_token(
            token, value, lineno, function_stack, last_name, current_fstring_start
        )
