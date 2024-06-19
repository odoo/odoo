# Code modified from babel version 2.15.0 (https://github.com/python-babel/babel/blob/v2.15.0)

from __future__ import annotations

import ast
import io
import re
import tokenize
from textwrap import dedent
from tokenize import COMMENT, NAME, OP, STRING, generate_tokens
from typing import TYPE_CHECKING, NamedTuple

from babel.util import parse_encoding, parse_future_flags

if TYPE_CHECKING:
    from collections.abc import Collection, Generator, Mapping
    from typing import IO, Protocol

    from _typeshed import SupportsRead, SupportsReadline
    from typing_extensions import TypeAlias, TypedDict

    class _PyOptions(TypedDict, total=False):
        encoding: str

    class _JSOptions(TypedDict, total=False):
        encoding: str
        jsx: bool
        template_string: bool
        parse_template_string: bool

    class _FileObj(SupportsRead[bytes], SupportsReadline[bytes], Protocol):
        def seek(self, __offset: int, __whence: int = ...) -> int: ...
        def tell(self) -> int: ...

    _SimpleKeyword: TypeAlias = tuple[int | tuple[int, int] | tuple[int, str], ...] | None
    _Keyword: TypeAlias = dict[int | None, _SimpleKeyword] | _SimpleKeyword

    # 4-tuple of (lineno, message, comments, context)
    _ExtractionResult: TypeAlias = tuple[int, str | tuple[str, ...], list[str], str | None]

# New tokens in Python 3.12, or None on older versions
FSTRING_START = getattr(tokenize, "FSTRING_START", None)
FSTRING_MIDDLE = getattr(tokenize, "FSTRING_MIDDLE", None)
FSTRING_END = getattr(tokenize, "FSTRING_END", None)


def extract_python(
    fileobj: IO[bytes],
    keywords: Mapping[str, _Keyword],
    comment_tags: Collection[str],
    options: _PyOptions,
) -> Generator[_ExtractionResult, None, None]:
    """Extract messages from Python source code.

    It returns an iterator yielding tuples in the following form ``(lineno,
    funcname, message, comments)``.

    :param fileobj: the seekable, file-like object the messages should be
                    extracted from
    :param keywords: a list of keywords (i.e. function names) that should be
                     recognized as translation functions
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
    :rtype: ``iterator``
    """
    funcname = lineno = message_lineno = None
    # MOD: This keeps track of the stack of nested function calls (to go back when exiting them)
    funcname_stack = []
    # MOD: This keeps track of whether we encountered a function call in the current stackframe
    funccall_in_frame = False
    # MOD: This keeps track of whether we encountered a string concatenation operator (+)
    concat_with_prev = False
    call_stack = -1
    buf = []
    messages = []
    translator_comments = []
    in_def = in_translator_comments = False
    comment_tag = None

    encoding = parse_encoding(fileobj) or options.get("encoding", "UTF-8")
    future_flags = parse_future_flags(fileobj, encoding)

    def next_line():
        return fileobj.readline().decode(encoding)

    tokens = generate_tokens(next_line)

    # Current prefix of a Python 3.12 (PEP 701) f-string, or None if we're not
    # currently parsing one.
    current_fstring_start = None

    for tok, value, (lineno, _), _, _ in tokens:
        if call_stack == -1 and tok == NAME and value in ("def", "class"):
            in_def = True
        elif tok == OP and value == "(":
            if in_def:
                # Avoid false positives for declarations such as:
                # def gettext(arg='message'):
                in_def = False
                continue
            if funcname:
                message_lineno = lineno
                call_stack += 1
                # MOD: Pushing the current function name on the stack and starting a new stackframe
                funcname_stack.append(funcname)
                funccall_in_frame = False
        elif in_def and tok == OP and value == ":":
            # End of a class definition without parens
            in_def = False
            continue
        elif call_stack == -1 and tok == COMMENT:
            # Strip the comment token from the line
            value = value[1:].strip()
            if in_translator_comments and \
                    translator_comments[-1][0] == lineno - 1:
                # We're already inside a translator comment, continue appending
                translator_comments.append((lineno, value))
                continue
            # If execution reaches this point, let's see if comment line
            # starts with one of the comment tags
            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    in_translator_comments = True
                    translator_comments.append((lineno, value))
                    break
        elif funcname and call_stack >= 0:
            # MOD: We allow for more than 1 stack depth now
            # MOD: We consider deeply nested calls (_() inside another function call) as well
            nested = tok == NAME
            closing_parenthesis = tok == OP and value == ")"
            if closing_parenthesis or nested:
                # MOD: We discard concatenation with a variable or a function call
                if concat_with_prev:
                    buf.clear()
                    concat_with_prev = False

                if buf:
                    messages.append("".join(buf))
                    buf.clear()
                else:
                    messages.append(None)

                messages = tuple(messages) if len(messages) > 1 else messages[0]
                # Comments don't apply unless they immediately
                # precede the message
                if translator_comments and \
                        translator_comments[-1][0] < message_lineno - 1:
                    translator_comments = []

                if funcname in keywords and messages is not None:
                    # MOD: We only yield when we're in the right function and our message is not empty
                    yield (message_lineno, funcname, messages,
                           [comment[1] for comment in translator_comments])

                funcname = lineno = message_lineno = None
                messages = []
                translator_comments = []
                in_translator_comments = False
                if closing_parenthesis:
                    # MOD: Remove the last stackframe and set the previous frame's function name again
                    call_stack -= 1
                    funcname_stack.pop()
                    if funcname_stack:
                        funcname = funcname_stack[-1]
                    funccall_in_frame = True
                if nested:
                    funcname = value
            elif tok == STRING and funcname in keywords and not funccall_in_frame:
                # MOD: Only consider strings when we're in a translation function and we didn't encounter
                # another function call before in this frame
                concat_with_prev = False
                val = _parse_python_string(value, encoding, future_flags)
                if val is not None:
                    buf.append(val)

            # Python 3.12+, see https://peps.python.org/pep-0701/#new-tokens
            elif tok == FSTRING_START:
                current_fstring_start = value
            elif tok == FSTRING_MIDDLE:
                if current_fstring_start is not None:
                    current_fstring_start += value
            elif tok == FSTRING_END:
                if current_fstring_start is not None and funcname in keywords and not funccall_in_frame:
                    # MOD: Only consider strings when we're in a translation function and we didn't encounter
                    # another function call before in this frame
                    fstring = current_fstring_start + value
                    val = _parse_python_string(fstring, encoding, future_flags)
                    if val is not None:
                        buf.append(val)
                else:
                    current_fstring_start = None

            elif tok == OP:
                if value == ",":
                    if buf:
                        messages.append("".join(buf))
                        buf.clear()
                    else:
                        messages.append(None)
                    if translator_comments:
                        # We have translator comments, and since we're on a
                        # comma(,) user is allowed to break into a new line
                        # Let's increase the last comment's lineno in order
                        # for the comment to still be a valid one
                        old_lineno, old_comment = translator_comments.pop()
                        translator_comments.append((old_lineno + 1, old_comment))
                elif value == "+":
                    # MOD: Support concatenating static strings
                    concat_with_prev = True
                else:
                    # MOD: Don't support other operators. We empty the buffer in that case.
                    buf.clear()
        elif funcname and call_stack == -1:
            funcname = None
        elif tok == NAME and value in keywords:
            funcname = value

        if (current_fstring_start is not None
            and tok not in {FSTRING_START, FSTRING_MIDDLE}
        ):
            # In Python 3.12, tokens other than FSTRING_* mean the
            # f-string is dynamic, so we don't wan't to extract it.
            # And if it's FSTRING_END, we've already handled it above.
            # Let's forget that we're in an f-string.
            current_fstring_start = None


def _parse_python_string(value: str, encoding: str, future_flags: int) -> str | None:
    # Unwrap quotes in a safe manner, maintaining the string's encoding
    # https://sourceforge.net/tracker/?func=detail&atid=355470&aid=617979&group_id=5470
    code = compile(
        f"# coding={encoding!s}\n{value}",
        "<string>",
        "eval",
        ast.PyCF_ONLY_AST | future_flags,
    )
    if isinstance(code, ast.Expression):
        body = code.body
        if isinstance(body, ast.Constant):
            return body.value
        if isinstance(body, ast.JoinedStr):  # f-string
            if all(isinstance(node, ast.Constant) for node in body.values):
                return "".join(node.value for node in body.values)
            # TODO: we could raise an error or warning when not all nodes are constants
    return None


def extract_javascript(
    fileobj: _FileObj,
    keywords: Mapping[str, _Keyword],
    comment_tags: Collection[str],
    options: _JSOptions,
    lineno: int = 1,
) -> Generator[_ExtractionResult, None, None]:
    """Extract messages from JavaScript source code.

    :param fileobj: the seekable, file-like object the messages should be
                    extracted from
    :param keywords: a list of keywords (i.e. function names) that should be
                     recognized as translation functions
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
                    Supported options are:
                    * `jsx` -- set to false to disable JSX/E4X support.
                    * `template_string` -- if `True`, supports gettext(`key`)
                    * `parse_template_string` -- if `True` will parse the
                                                 contents of javascript
                                                 template strings.
    :param lineno: line number offset (for parsing embedded fragments)
    """
    operators: list[str] = sorted([
        '+', '-', '*', '%', '!=', '==', '<', '>', '<=', '>=', '=',
        '+=', '-=', '*=', '%=', '<<', '>>', '>>>', '<<=', '>>=',
        '>>>=', '&', '&=', '|', '|=', '&&', '||', '^', '^=', '(', ')',
        '[', ']', '{', '}', '!', '--', '++', '~', ',', ';', '.', ':',
    ], key=len, reverse=True)

    escapes: dict[str, str] = {'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t'}

    name_re = re.compile(r'[\w$_][\w\d$_]*', re.UNICODE)
    dotted_name_re = re.compile(r'[\w$_][\w\d$_.]*[\w\d$_.]', re.UNICODE)
    division_re = re.compile(r'/=?')
    regex_re = re.compile(r'/(?:[^/\\]*(?:\\.[^/\\]*)*)/[a-zA-Z]*', re.DOTALL)
    line_re = re.compile(r'(\r\n|\n|\r)')
    line_join_re = re.compile(r'\\' + line_re.pattern)
    uni_escape_re = re.compile(r'[a-fA-F0-9]{1,4}')
    hex_escape_re = re.compile(r'[a-fA-F0-9]{1,2}')

    class Token(NamedTuple):
        type: str
        value: str
        lineno: int

    _rules: list[tuple[str | None, re.Pattern[str]]] = [
        (None, re.compile(r'\s+', re.UNICODE)),
        (None, re.compile(r'<!--.*')),
        ('linecomment', re.compile(r'//.*')),
        ('multilinecomment', re.compile(r'/\*.*?\*/', re.UNICODE | re.DOTALL)),
        ('dotted_name', dotted_name_re),
        ('name', name_re),
        ('number', re.compile(r'''(
            (?:0|[1-9]\d*)
            (\.\d+)?
            ([eE][-+]?\d+)? |
            (0x[a-fA-F0-9]+)
        )''', re.VERBOSE)),
        ('jsx_tag', re.compile(r'(?:</?[^>\s]+|/>)', re.IGNORECASE)),  # May be mangled in `get_rules`
        ('operator', re.compile(r'(%s)' % '|'.join(map(re.escape, operators)))),
        ('template_string', re.compile(r'''`(?:[^`\\]*(?:\\.[^`\\]*)*)`''', re.UNICODE)),
        ('string', re.compile(r'''(
            '(?:[^'\\]*(?:\\.[^'\\]*)*)'  |
            "(?:[^"\\]*(?:\\.[^"\\]*)*)"
        )''', re.VERBOSE | re.DOTALL)),
    ]

    def get_rules(jsx: bool, dotted: bool, template_string: bool) -> list[tuple[str | None, re.Pattern[str]]]:
        """
        Get a tokenization rule list given the passed syntax options.

        Internal to this module.
        """
        rules = []
        for token_type, rule in _rules:
            if not jsx and token_type and "jsx" in token_type:
                continue
            if not template_string and token_type == "template_string":
                continue
            if token_type == "dotted_name":
                if not dotted:
                    continue
                token_type = "name"
            rules.append((token_type, rule))
        return rules

    def indicates_division(token: Token) -> bool:
        """A helper function that helps the tokenizer to decide if the current
        token may be followed by a division operator.
        """
        if token.type == "operator":
            return token.value in (")", "]", "}", "++", "--")
        return token.type in ("name", "number", "string", "regexp")

    def unquote_string(string: str) -> str:
        """Unquote a string with JavaScript rules.  The string has to start with
        string delimiters (``'``, ``"`` or the back-tick/grave accent (for template strings).)
        """
        assert string and string[0] == string[-1] and string[0] in "\"'`", "string provided is not properly delimited"
        string = line_join_re.sub("\\1", string[1:-1])
        result: list[str] = []
        add = result.append
        pos = 0

        while True:
            # scan for the next escape
            escape_pos = string.find("\\", pos)
            if escape_pos < 0:
                break
            add(string[pos:escape_pos])

            # check which character is escaped
            next_char = string[escape_pos + 1]
            if next_char in escapes:
                add(escapes[next_char])

            # unicode escapes.  trie to consume up to four characters of
            # hexadecimal characters and try to interpret them as unicode
            # character point.  If there is no such character point, put
            # all the consumed characters into the string.
            elif next_char in "uU":
                escaped = uni_escape_re.match(string, escape_pos + 2)
                if escaped is not None:
                    escaped_value = escaped.group()
                    if len(escaped_value) == 4:
                        try:
                            add(chr(int(escaped_value, 16)))
                        except ValueError:
                            pass
                        else:
                            pos = escape_pos + 6
                            continue
                    add(next_char + escaped_value)
                    pos = escaped.end()
                    continue
                else:
                    add(next_char)

            # hex escapes. conversion from 2-digits hex to char is infallible
            elif next_char in "xX":
                escaped = hex_escape_re.match(string, escape_pos + 2)
                if escaped is not None:
                    escaped_value = escaped.group()
                    add(chr(int(escaped_value, 16)))
                    pos = escape_pos + 2 + len(escaped_value)
                    continue
                else:
                    add(next_char)

            # bogus escape.  Just remove the backslash.
            else:
                add(next_char)
            pos = escape_pos + 2

        if pos < len(string):
            add(string[pos:])

        return "".join(result)

    def tokenize(
        source: str, jsx: bool = True, dotted: bool = True, template_string: bool = True, lineno: int = 1
    ) -> Generator[Token, None, None]:
        """
        Tokenize JavaScript/JSX source.  Returns a generator of tokens.

        :param jsx: Enable (limited) JSX parsing.
        :param dotted: Read dotted names as single name token.
        :param template_string: Support ES6 template strings
        :param lineno: starting line number (optional)
        """
        may_divide = False
        pos = 0
        end = len(source)
        rules = get_rules(jsx=jsx, dotted=dotted, template_string=template_string)

        while pos < end:
            # handle regular rules first
            for token_type, rule in rules:
                match = rule.match(source, pos)
                if match is not None:
                    break
            # if we don't have a match we don't give up yet, but check for
            # division operators or regular expression literals, based on
            # the status of `may_divide` which is determined by the last
            # processed non-whitespace token using `indicates_division`.
            else:
                if may_divide:
                    match = division_re.match(source, pos)
                    token_type = "operator"
                else:
                    match = regex_re.match(source, pos)
                    token_type = "regexp"
                if match is None:
                    # woops. invalid syntax. jump one char ahead and try again.
                    pos += 1
                    continue

            token_value = match.group()
            if token_type is not None:
                token = Token(token_type, token_value, lineno)
                may_divide = indicates_division(token)
                yield token
            lineno += len(line_re.findall(token_value))
            pos = match.end()

    funcname = message_lineno = None
    # MOD: This keeps track of the stack of nested function calls (to go back when exiting them)
    funcname_stack = []
    # MOD: This keeps track of whether we encountered a function call in the current stackframe
    funccall_in_frame = False
    # MOD: This keeps track of whether we encountered a string concatenation operator (+)
    concat_with_prev = False
    call_stack = -1
    buf = []
    messages = []
    translator_comments = []
    encoding = options.get("encoding", "utf-8")
    last_token = None
    dotted = any("." in kw for kw in keywords)
    for token in tokenize(
        fileobj.read().decode(encoding),
        jsx=options.get("jsx", True),
        template_string=options.get("template_string", True),
        dotted=dotted,
        lineno=lineno,
    ):
        if (  # Turn keyword`foo` expressions into keyword("foo") calls:
            funcname  # have a keyword...
            and (last_token and last_token.type == "name")  # we've seen nothing after the keyword...
            and token.type == "template_string"  # this is a template string
        ):
            message_lineno = token.lineno
            if funcname in keywords:
                # MOD: Only consider the string if we're in a translation function
                messages = [unquote_string(token.value)]
            # MOD: We enter a function call: add it to the stack and reset funccall_in_frame
            call_stack += 1
            funcname_stack.append(funcname)
            funccall_in_frame = False
            token = Token("operator", ")", token.lineno)

        if options.get("parse_template_string") and not funcname and token.type == "template_string":
            yield from parse_template_string(token.value, keywords, comment_tags, options, token.lineno)

        elif token.type == "operator" and token.value == "(":
            if funcname:
                message_lineno = token.lineno
                # MOD: We enter a function call: add it to the stack and reset funccall_in_frame
                call_stack += 1
                funcname_stack.append(funcname)
                funccall_in_frame = False

        elif call_stack == -1 and token.type == "linecomment":
            value = token.value[2:].strip()
            if translator_comments and translator_comments[-1][0] == token.lineno - 1:
                translator_comments.append((token.lineno, value))
                continue

            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    translator_comments.append((token.lineno, value.strip()))
                    break

        elif token.type == "multilinecomment":
            # only one multi-line comment may precede a translation
            translator_comments = []
            value = token.value[2:-2].strip()
            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    lines = value.splitlines()
                    if lines:
                        lines[0] = lines[0].strip()
                        lines[1:] = dedent("\n".join(lines[1:])).splitlines()
                        for offset, line in enumerate(lines):
                            translator_comments.append((token.lineno + offset, line))
                    break

        elif funcname and call_stack >= 0:
            # MOD: We allow for more than 1 stack depth now
            # MOD: We consider deeply nested calls (_t() inside another function call) as well
            nested = token.type == "name"
            closing_parenthesis = token.type == "operator" and token.value == ")"
            if closing_parenthesis or nested:
                # MOD: We discard concatenation with a variable or a function call
                if concat_with_prev:
                    buf.clear()
                    concat_with_prev = False

                if buf:
                    messages.append("".join(buf))
                    buf.clear()
                else:
                    messages.append(None)

                messages = tuple(messages) if len(messages) > 1 else messages[0]
                # Comments don't apply unless they immediately precede the
                # message
                if translator_comments and translator_comments[-1][0] < message_lineno - 1:
                    translator_comments = []

                if funcname in keywords and messages is not None:
                    # MOD: We only yield when we're in the right function and our message is not empty
                    yield (message_lineno, funcname, messages, [comment[1] for comment in translator_comments])

                funcname = message_lineno = None
                translator_comments = []
                messages = []
                if closing_parenthesis:
                    # MOD: Remove the last stackframe and set the previous frame's function name again
                    call_stack -= 1
                    funcname_stack.pop()
                    if funcname_stack:
                        funcname = funcname_stack[-1]
                    funccall_in_frame = True
                if nested:
                    funcname = token.value

            elif token.type in ("string", "template_string") and funcname in keywords and not funccall_in_frame:
                # MOD: Only consider strings when we're in a translation function and we didn't encounter
                # another function call before in this frame
                concat_with_prev = False
                new_value = unquote_string(token.value)
                if new_value is not None:
                    buf.append(new_value)

            elif token.type == "operator":
                if token.value == ",":
                    if buf:
                        messages.append("".join(buf))
                        buf.clear()
                    else:
                        messages.append(None)
                elif token.value == "+":
                    concat_with_prev = True
                else:
                    # MOD: Don't support other operators. We empty the buffer in that case.
                    buf.clear()

        elif funcname and call_stack == -1:
            funcname = None

        elif (
            token.type == "name"
            and token.value in keywords
            and (last_token is None or last_token.type != "name" or last_token.value != "function")
        ):
            funcname = token.value

        last_token = token


def parse_template_string(
    template_string: str,
    keywords: Mapping[str, _Keyword],
    comment_tags: Collection[str],
    options: _JSOptions,
    lineno: int = 1,
) -> Generator[_ExtractionResult, None, None]:
    """Parse JavaScript template string.

    :param template_string: the template string to be parsed
    :param keywords: a list of keywords (i.e. function names) that should be
                     recognized as translation functions
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
    :param lineno: starting line number (optional)
    """
    line_re = re.compile(r"(\r\n|\n|\r)")

    prev_character = None
    level = 0
    inside_str = False
    expression_contents = ""
    for character in template_string[1:-1]:
        if not inside_str and character in ('"', "'", "`"):
            inside_str = character
        elif inside_str == character and prev_character != r"\\":
            inside_str = False
        if level:
            expression_contents += character
        if not inside_str:
            if character == "{" and prev_character == "$":
                level += 1
            elif level and character == "}":
                level -= 1
                if level == 0 and expression_contents:
                    expression_contents = expression_contents[0:-1]
                    fake_file_obj = io.BytesIO(expression_contents.encode())
                    yield from extract_javascript(fake_file_obj, keywords, comment_tags, options, lineno)
                    lineno += len(line_re.findall(expression_contents))
                    expression_contents = ""
        prev_character = character


def patch_babel():
    try:
        import babel.messages.extract  # noqa: PLC0415
    except ImportError:
        pass
    else:
        # Patch the babel library to also extract deeply nested gettext calls.
        # e.g. _("Text %s", other_function(_("Deeply Nested")))
        babel.messages.extract.extract_python = extract_python
        babel.messages.extract.extract_javascript = extract_javascript
