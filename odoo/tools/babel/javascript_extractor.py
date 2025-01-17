from __future__ import annotations

import io
from textwrap import dedent
from typing import TYPE_CHECKING

from babel.messages.jslexer import Token, line_re, tokenize, unquote_string

if TYPE_CHECKING:
    from collections.abc import Collection, Generator, Mapping
    from typing import Protocol, TypeAlias, TypedDict

    from _typeshed import SupportsRead, SupportsReadline

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

    # The file object to pass to the extraction function
    class _FileObj(SupportsRead[bytes], SupportsReadline[bytes], Protocol):
        def seek(self, offset: int, whence: int = ..., /) -> int: ...
        def tell(self) -> int: ...

    # The possible options to pass to the extraction function
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
) -> Generator[_ExtractionResult, None, None]:
    prev_character = None
    level = 0
    inside_str = False
    expression_contents = ''
    for character in template_string[1:-1]:
        if not inside_str and character in ('"', "'", '`'):
            inside_str = character
        elif inside_str == character and prev_character != r'\\':
            inside_str = False
        if level or keyword:
            expression_contents += character
        if not inside_str:
            if character == '{' and prev_character == '$':
                if keyword:
                    break
                level += 1
            elif level and character == '}':
                level -= 1
                if level == 0 and expression_contents:
                    expression_contents = expression_contents[0:-1]
                    fake_file_obj = io.BytesIO(expression_contents.encode())
                    yield from extract_javascript(fake_file_obj, keywords, comment_tags, options, lineno)
                    lineno += len(line_re.findall(expression_contents))
                    expression_contents = ''
        prev_character = character
    if keyword:
        yield (lineno, keyword, expression_contents, [])


def extract_javascript(
    fileobj: _FileObj,
    keywords: Mapping[str, _Keyword],
    comment_tags: Collection[str],
    options: _JSOptions,
    lineno_offset: int = 0,
) -> Generator[_ExtractionResult, None, None]:
    """
    Extract all translatable terms from a Javascript source file.

    This function is modified from the official Babel extractor to support arbitrarily nested function calls.

    :param fileobj: The Javascript source file
    :param keywords: The translation keywords mapping
    :param comment_tags: The keywords to extract translator comments
    :param options: Extractor options for parsing the Javascript file
    :yield: Tuples in the following form: `(lineno, funcname, message, comments)`
    """
    encoding = options.get('encoding', 'utf-8')
    dotted = any('.' in kw for kw in keywords)

    # Keep track of the last token we saw.
    last_token = None
    # Keep the stack of all function calls and its related contextual variables, so we can handle nested gettext calls.
    function_stack = []
    # Keep track of whether we're in a class or function definition.
    in_def = False
    # Keep track of whether we're in a block of translator comments.
    in_translator_comments = False
    # Keep track of the last encountered translator comments.
    translator_comments = []
    # Keep track of the (split) strings encountered.
    message_buffer = []

    for token in tokenize(
        fileobj.read().decode(encoding),
        jsx=options.get('jsx', True),
        dotted=dotted,
        template_string=options.get('template_string', True),
    ):
        token: Token = Token(token.type, token.value, token.lineno + lineno_offset)
        if token.type == 'name' and token.value in ('class', 'function'):
            # We're entering a class or function definition.
            in_def = True
            continue

        elif in_def and token.type == 'operator' and token.value in ('(', '{'):
            # We're in a class or function definition and should not do anything.
            in_def = False
            continue

        elif (
            last_token
            and last_token.type == 'name'
            and token.type == 'template_string'
        ):
            # Turn keyword`foo` expressions into keyword("foo") function calls.
            string_value = unquote_string(token.value)
            cur_translator_comments = translator_comments
            if function_stack and function_stack[-1]['function_lineno'] == last_token.lineno:
                # If our current function call is on the same line as the previous one,
                # copy their translator comments, since they also apply to us.
                cur_translator_comments = function_stack[-1]['translator_comments']

            # We add all information needed later for the current function call.
            function_stack.append({
                'function_lineno': last_token.lineno,
                'function_name': last_token.value,
                'message_lineno': token.lineno,
                'messages': [string_value],
                'translator_comments': cur_translator_comments,
            })
            translator_comments = []
            message_buffer.clear()

            # We act as if we are closing the function call now
            last_token = token
            token = Token('operator', ')', token.lineno)

        if (
            options.get('parse_template_string', True)
            and (not last_token or last_token.type != 'name' or last_token.value not in keywords)
            and token.type == 'template_string'
        ):
            keyword = ""
            if function_stack and function_stack[-1]['function_name'] in keywords:
                keyword = function_stack[-1]['function_name']
            yield from parse_template_string(
                token.value,
                keywords,
                comment_tags,
                options,
                token.lineno,
                keyword,
            )

        elif token.type == 'operator' and token.value == '(':
            if last_token and last_token.type == 'name':
                # We're entering a function call.
                cur_translator_comments = translator_comments
                if function_stack and function_stack[-1]['function_lineno'] == last_token.lineno:
                    # If our current function call is on the same line as the previous one,
                    # copy their translator comments, since they also apply to us.
                    cur_translator_comments = function_stack[-1]['translator_comments']

                # We add all information needed later for the current function call.
                function_stack.append({
                    'function_lineno': token.lineno,
                    'function_name': last_token.value,
                    'message_lineno': None,
                    'messages': [],
                    'translator_comments': cur_translator_comments,
                })
                translator_comments = []
                message_buffer.clear()

        elif token.type == 'linecomment':
            # Strip the comment character from the line.
            value = token.value[2:].strip()
            if in_translator_comments and translator_comments[-1][0] == token.lineno - 1:
                # We're already in a translator comment. Continue appending.
                translator_comments.append((token.lineno, value))
                continue

            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    # The comment starts with one of the translator comment keywords, so let's start capturing it.
                    in_translator_comments = True
                    translator_comments.append((token.lineno, value))
                    break

        elif token.type == 'multilinecomment':
            # Only one multi-line comment may precede a translation.
            translator_comments = []
            value = token.value[2:-2].strip()
            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    lines = value.splitlines()
                    if lines:
                        lines[0] = lines[0].strip()
                        lines[1:] = dedent('\n'.join(lines[1:])).splitlines()
                        for offset, line in enumerate(lines):
                            translator_comments.append((token.lineno + offset, line))
                    break

        elif function_stack and function_stack[-1]['function_name'] in keywords:
            # We're inside a translation function call.
            if token.type == 'operator' and token.value == ')':
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

            elif token.type in ('string', 'template_string'):
                # We've encountered a string inside a translation function call.
                if last_token.type == 'name':
                    message_buffer.clear()
                else:
                    string_value = unquote_string(token.value)
                    if not function_stack[-1]['message_lineno']:
                        function_stack[-1]['message_lineno'] = token.lineno
                    if string_value is not None:
                        message_buffer.append(string_value)

            elif token.type == 'operator' and token.value == ',':
                # We're at the end of a function call argument.
                if message_buffer:
                    function_stack[-1]['messages'].append(''.join(message_buffer))
                    message_buffer.clear()
                else:
                    function_stack[-1]['messages'].append(None)

        elif function_stack and token.type == 'operator' and token.value == ')':
            function_stack.pop()

        if in_translator_comments and translator_comments[-1][0] < token.lineno:
            # We have a newline between the comment lines, so they don't belong together anymore.
            in_translator_comments = False

        last_token = token
