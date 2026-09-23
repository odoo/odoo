import io
from textwrap import dedent
from typing import TYPE_CHECKING

from babel.messages.jslexer import Token, line_re, tokenize, unquote_string

from ._frames import (
    Frame,
    close_keyword_frame,
    handle_line_comment,
    open_keyword_name,
    push_function_frame,
)

type _SimpleKeyword = tuple[int | tuple[int, int] | tuple[int, str], ...] | None
type _Keyword = dict[int | None, _SimpleKeyword] | _SimpleKeyword
type _ExtractionResult = tuple[int, str, str | tuple[str, ...], list[str]]

if TYPE_CHECKING:
    from collections.abc import Collection, Generator, Mapping
    from typing import Protocol, TypedDict

    from _typeshed import SupportsRead, SupportsReadline

    class _FileObj(SupportsRead[bytes], SupportsReadline[bytes], Protocol):
        def seek(self, offset: int, whence: int = ..., /) -> int: ...
        def tell(self) -> int: ...

    class _JSOptions(TypedDict, total=False):
        encoding: str
        jsx: bool
        template_string: bool
        parse_template_string: bool


def parse_template_string(
    template_string: str,
    keywords: Mapping[str, _Keyword],
    comment_tags: Collection[str],
    options: _JSOptions,
    lineno: int = 0,
    keyword: str = "",
) -> Generator[_ExtractionResult]:
    prev_character = None
    escaped = False
    level = 0
    inside_str = ""
    expression_contents = ""
    for character in template_string[1:-1]:
        if not inside_str and character in ('"', "'", "`"):
            inside_str = character
        elif inside_str == character and not escaped:
            inside_str = ""
        if level or keyword:
            expression_contents += character
        if not inside_str:
            if character == "{" and prev_character == "$":
                if keyword:
                    break
                level += 1
            elif level and character == "}":
                level -= 1
                if level == 0 and expression_contents:
                    expression_contents = expression_contents[0:-1]
                    fake_file_obj = io.BytesIO(expression_contents.encode())
                    yield from extract_javascript(
                        fake_file_obj, keywords, comment_tags, options, lineno - 1
                    )
                    lineno += len(line_re.findall(expression_contents))
                    expression_contents = ""
        escaped = character == "\\" and not escaped
        prev_character = character
    if keyword:
        yield (lineno, keyword, expression_contents, [])


def _multiline_translator_comments(
    value: str, comment_tags: Collection[str], lineno: int
) -> list[tuple[int, str]]:
    for comment_tag in comment_tags:
        if not value.startswith(comment_tag):
            continue
        lines = value.splitlines()
        if not lines:
            return []
        lines[0] = lines[0].strip()
        lines[1:] = dedent("\n".join(lines[1:])).splitlines()
        return [(lineno + offset, line) for offset, line in enumerate(lines)]
    return []


def _collect_keyword_message(
    token: Token,
    last_token: Token,
    function_stack: list[Frame],
    message_buffer: list[str],
) -> None:
    if token.type in ("string", "template_string"):
        if last_token.type == "name":
            message_buffer.clear()
            return
        string_value = unquote_string(token.value)
        if not function_stack[-1]["message_lineno"]:
            function_stack[-1]["message_lineno"] = token.lineno
        if string_value is not None:
            message_buffer.append(string_value)
    elif token.type == "operator" and token.value == ",":
        if message_buffer:
            function_stack[-1]["messages"].append("".join(message_buffer))
            message_buffer.clear()
        else:
            function_stack[-1]["messages"].append(None)


def _js_tokens(
    fileobj: _FileObj,
    keywords: Mapping[str, _Keyword],
    options: _JSOptions,
    lineno_offset: int,
) -> Generator[Token]:
    encoding = options.get("encoding", "utf-8")
    for token in tokenize(
        fileobj.read().decode(encoding),
        jsx=options.get("jsx", True),
        dotted=any("." in kw for kw in keywords),
        template_string=options.get("template_string", True),
    ):
        yield Token(token.type, token.value, token.lineno + lineno_offset)


def _js_comment_token(
    token: Token,
    comment_tags: Collection[str],
    in_translator_comments: bool,
    translator_comments: list[tuple[int, str]],
) -> tuple[bool, list[tuple[int, str]], bool]:
    if token.type == "multilinecomment":
        return (
            in_translator_comments,
            _multiline_translator_comments(
                token.value[2:-2].strip(), comment_tags, token.lineno
            ),
            False,
        )
    in_translator_comments, skip = handle_line_comment(
        token.value[2:].strip(),
        token.lineno,
        comment_tags,
        in_translator_comments,
        translator_comments,
    )
    return in_translator_comments, translator_comments, skip


def _is_bare_template_string(
    token: Token,
    last_token: Token | None,
    keywords: Mapping[str, _Keyword],
    options: _JSOptions,
    function_stack: list[Frame],
) -> bool:
    return bool(
        options.get("parse_template_string", True)
        and (
            not last_token
            or last_token.type != "name"
            or last_token.value not in keywords
        )
        and (not function_stack or function_stack[-1]["function_name"] not in keywords)
        and token.type == "template_string"
    )


def _continues_definition(token: Token) -> bool:
    return token.type in ("name", "linecomment", "multilinecomment") or (
        token.type == "operator" and token.value == "*"
    )


def extract_javascript(
    fileobj: _FileObj,
    keywords: Mapping[str, _Keyword],
    comment_tags: Collection[str],
    options: _JSOptions,
    lineno_offset: int = 0,
) -> Generator[_ExtractionResult]:
    last_token = None
    function_stack: list[Frame] = []
    in_def = in_translator_comments = False
    translator_comments: list[tuple[int, str]] = []
    message_buffer: list[str] = []

    for token in _js_tokens(fileobj, keywords, options, lineno_offset):
        if token.type == "name" and token.value in ("class", "function"):
            in_def = True
            continue

        if in_def:
            if token.type == "operator" and token.value in ("(", "{"):
                in_def = False
                continue
            in_def = _continues_definition(token)

        if (
            last_token
            and last_token.type == "name"
            and last_token.value in keywords
            and token.type == "template_string"
        ):
            translator_comments = push_function_frame(
                function_stack,
                translator_comments,
                message_buffer,
                compare_lineno=last_token.lineno,
                function_lineno=last_token.lineno,
                function_name=last_token.value,
                message_lineno=token.lineno,
                messages=[],
            )
            message_buffer.append(unquote_string(token.value))
            last_token = token
            token = Token("operator", ")", token.lineno)

        if _is_bare_template_string(
            token, last_token, keywords, options, function_stack
        ):
            yield from parse_template_string(
                token.value,
                keywords,
                comment_tags,
                options,
                token.lineno,
                open_keyword_name(function_stack, keywords),
            )

        elif token.type == "operator" and token.value == "(":
            if last_token and last_token.type == "name":
                translator_comments = push_function_frame(
                    function_stack,
                    translator_comments,
                    message_buffer,
                    compare_lineno=last_token.lineno,
                    function_lineno=token.lineno,
                    function_name=last_token.value,
                    message_lineno=None,
                    messages=[],
                )

        elif token.type in ("linecomment", "multilinecomment"):
            in_translator_comments, translator_comments, skip = _js_comment_token(
                token, comment_tags, in_translator_comments, translator_comments
            )
            if skip:
                continue

        elif function_stack and function_stack[-1]["function_name"] in keywords:
            if token.type == "operator" and token.value == ")":
                yield close_keyword_frame(function_stack, message_buffer)
            else:
                _collect_keyword_message(
                    token, last_token, function_stack, message_buffer
                )
        elif function_stack and token.type == "operator" and token.value == ")":
            function_stack.pop()

        if in_translator_comments and translator_comments[-1][0] < token.lineno:
            in_translator_comments = False

        last_token = token
