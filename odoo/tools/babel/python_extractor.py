from __future__ import annotations

import ast
import tokenize
from tokenize import COMMENT, NAME, OP, STRING, generate_tokens
from typing import TYPE_CHECKING

from babel.util import parse_encoding, parse_future_flags

if TYPE_CHECKING:
    from collections.abc import Collection, Generator, Mapping
    from typing import IO, TypeAlias, TypedDict

    """
    Types used by the extractor
    """
    # Tuple specifying which of the translation function's arguments contains localizable strings.
    #   e.g. (1, 2)
    #   -> Indicates the first and second argument are translatable terms, like in `ngettext`
    #   e.g. ((1, 'c'), 2)
    #   -> Indicates the first argument is a context key and the second is the translatable term, like in `pgettext`
    #   e.g. None
    #   -> Indicates there is only one argument translatable, like in `gettext`
    _SimpleKeyword: TypeAlias = tuple[int | tuple[int, int] | tuple[int, str], ...] | None
    # A `_SimpleKeyword` or a `dict` mapping the expected number of function arguments against the `_SimpleKeyword`
    _Keyword: TypeAlias = dict[int | None, _SimpleKeyword] | _SimpleKeyword
    # The result of extracting terms, a 4-tuple containing:
    # (lineno: int, messages: str | tuple[str, ...], comments: list[str], context: str | None)
    #   - `lineno`: The line number of the extracted term(s)
    #   - `funcname`: The translation function name
    #   - `messages`: The extracted term(s). A single one or multiple in case of e.g. `ngettext`
    #   - `comments`: The extracted translator comments for the term(s)
    _ExtractionResult: TypeAlias = tuple[int, str, str | tuple[str, ...], list[str]]

    # The possible options to pass to the extraction function
    class _PyOptions(TypedDict, total=False):
        encoding: str


# New tokens in Python 3.12, or None on older versions
FSTRING_START = tokenize.FSTRING_START if hasattr(tokenize, 'FSTRING_START') else None
FSTRING_MIDDLE = tokenize.FSTRING_MIDDLE if hasattr(tokenize, 'FSTRING_MIDDLE') else None
FSTRING_END = tokenize.FSTRING_END if hasattr(tokenize, 'FSTRING_END') else None


def _parse_python_string(value: str, encoding: str, future_flags: int) -> str | None:
    # Unwrap quotes in a safe manner, maintaining the string's encoding
    code = compile(
        f'# coding={encoding!s}\n{value}',
        '<string>',
        'eval',
        ast.PyCF_ONLY_AST | future_flags,
    )
    if isinstance(code, ast.Expression):
        body = code.body
        if isinstance(body, ast.Constant):
            return body.value
        if isinstance(body, ast.JoinedStr):  # f-string
            if all(isinstance(node, ast.Constant) for node in body.values):
                return ''.join(node.value for node in body.values)
    return None


def extract_python(
    fileobj: IO[bytes],
    keywords: Mapping[str, _Keyword],
    comment_tags: Collection[str],
    options: _PyOptions,
) -> Generator[_ExtractionResult, None, None]:
    """
    Extract all translatable terms from a Python source file.

    This function is modified from the official Babel extractor to support arbitrarily nested function calls.

    :param fileobj: The Python source file
    :param keywords: The translation keywords (function names) mapping
    :param comment_tags: The keywords to extract translator comments
    :param options: Extractor options for parsing the Python file
    :yield: Tuples in the following form: `(lineno, funcname, message, comments)`
    """
    encoding = parse_encoding(fileobj) or options.get('encoding', 'utf-8')
    future_flags = parse_future_flags(fileobj, encoding)

    def next_line():
        return fileobj.readline().decode(encoding)

    tokens = generate_tokens(next_line)

    # Keep the stack of all function calls and its related contextual variables, so we can handle nested gettext calls.
    function_stack = []
    # Keep the last encountered function/variable name for when we encounter an opening parenthesis.
    last_name = None
    # Keep track of whether we're in a class or function definition.
    in_def = False
    # Keep track of whether we're in a block of translator comments.
    in_translator_comments = False
    # Keep track of the last encountered translator comments.
    translator_comments = []
    # Keep track of the (split) strings encountered.
    message_buffer = []
    # Current prefix of a Python 3.12 (PEP 701) f-string, or None if we're not currently parsing one.
    current_fstring_start = None

    for token, value, (lineno, _), _, _ in tokens:
        if token == NAME and value in ('def', 'class'):
            # We're entering a class or function definition.
            in_def = True
            continue

        if in_def and token == OP and value in ('(', ':'):
            # We're in a class or function definition and should not do anything.
            in_def = False
            continue

        if token == OP and value == '(' and last_name:
            # We're entering a function call.
            cur_translator_comments = translator_comments
            if function_stack and function_stack[-1]['function_lineno'] == lineno:
                # If our current function call is on the same line as the previous one,
                # copy their translator comments, since they also apply to us.
                cur_translator_comments = function_stack[-1]['translator_comments']

            # We add all information needed later for the current function call.
            function_stack.append({
                'function_lineno': lineno,
                'function_name': last_name,
                'message_lineno': None,
                'messages': [],
                'translator_comments': cur_translator_comments,
            })
            translator_comments = []
            message_buffer.clear()

        elif token == COMMENT:
            # Strip the comment character from the line.
            value = value[1:].strip()
            if in_translator_comments and translator_comments[-1][0] == lineno - 1:
                # We're already in a translator comment. Continue appending.
                translator_comments.append((lineno, value))
                continue

            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    # The comment starts with one of the translator comment keywords, so let's start capturing it.
                    in_translator_comments = True
                    translator_comments.append((lineno, value))
                    break

        elif function_stack and function_stack[-1]['function_name'] in keywords:
            # We're inside a translation function call.
            if token == OP and value == ')':
                # The call has ended, so we yield the translatable term(s).
                messages = function_stack[-1]['messages']
                lineno = function_stack[-1]['message_lineno'] or function_stack[-1]['function_lineno']
                cur_translator_comments = function_stack[-1]['translator_comments']

                if message_buffer:
                    messages.append(''.join(message_buffer))
                    message_buffer.clear()
                else:
                    messages.append(None)

                messages = tuple(messages) if len(messages) > 1 else messages[0]
                if cur_translator_comments and cur_translator_comments[-1][0] < lineno - 1:
                    # The translator comments are not immediately preceding the current term, so we skip them.
                    cur_translator_comments = []

                yield (
                    lineno,
                    function_stack[-1]['function_name'],
                    messages,
                    [comment[1] for comment in cur_translator_comments],
                )

                function_stack.pop()

            elif token == STRING:
                # We've encountered a string inside a translation function call.
                string_value = _parse_python_string(value, encoding, future_flags)
                if not function_stack[-1]['message_lineno']:
                    function_stack[-1]['message_lineno'] = lineno
                if string_value is not None:
                    message_buffer.append(string_value)

            # Python 3.12+, see https://peps.python.org/pep-0701/#new-tokens
            elif token == FSTRING_START:
                current_fstring_start = value
            elif token == FSTRING_MIDDLE:
                if current_fstring_start is not None:
                    current_fstring_start += value
            elif token == FSTRING_END:
                if current_fstring_start is not None:
                    fstring = current_fstring_start + value
                    string_value = _parse_python_string(fstring, encoding, future_flags)
                    if string_value is not None:
                        message_buffer.append(string_value)

            elif token == OP and value == ',':
                # End of a function call argument
                if message_buffer:
                    function_stack[-1]['messages'].append(''.join(message_buffer))
                    message_buffer.clear()
                else:
                    function_stack[-1]['messages'].append(None)

        elif function_stack and token == OP and value == ')':
            # This is the end of an non-translation function call. Just pop it from the stack.
            function_stack.pop()

        if in_translator_comments and translator_comments[-1][0] < lineno:
            # We have a newline between the comment lines, so they don't belong together anymore.
            in_translator_comments = False

        if token == NAME:
            last_name = value
            if function_stack and not function_stack[-1]['message_lineno']:
                function_stack[-1]['message_lineno'] = lineno

        if current_fstring_start is not None and token not in {FSTRING_START, FSTRING_MIDDLE}:
            # In Python 3.12, tokens other than FSTRING_* mean the f-string is dynamic,
            # so we don't wan't to extract it.
            # And if it's FSTRING_END, we've already handled it above.
            # Let's forget that we're in an f-string.
            current_fstring_start = None
