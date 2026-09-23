import re
from typing import NamedTuple

_CODE_STOP_RE = re.compile(r"[\"'`/{}]")
_TEMPLATE_STOP_RE = re.compile(r"\\[\s\S]|`|\$\{")
_STRING_RE = {
    '"': re.compile(r'"(?:[^"\\\n]|\\[\s\S])*"?'),
    "'": re.compile(r"'(?:[^'\\\n]|\\[\s\S])*'?"),
}
_REGEX_FLAGS_RE = re.compile(r"[A-Za-z]*")
_KEYWORDS_BEFORE_REGEX = frozenset(
    {
        "await",
        "case",
        "delete",
        "do",
        "else",
        "in",
        "instanceof",
        "new",
        "of",
        "return",
        "throw",
        "typeof",
        "void",
        "yield",
    }
)
_SPECIFIER_KEYWORDS = frozenset({"from", "import"})


def _token_before(src: str, pos: int) -> str:
    end = pos
    while end and src[end - 1].isspace():
        end -= 1
    if not end:
        return ""
    start = end
    while start and (src[start - 1].isalnum() or src[start - 1] in "_$"):
        start -= 1
    return src[start:end] if start < end else src[end - 1]


class Span(NamedTuple):
    kind: str
    start: int
    end: int


class _Scanner:
    __slots__ = ("depth", "nested", "spans", "src")

    def __init__(self, src: str) -> None:
        self.src = src
        self.spans: list[Span] = []
        self.nested = False
        self.depth = 0

    def _opaque(self, kind: str, start: int, end: int) -> None:
        if self.depth:
            if "`" in self.src[start:end]:
                self.nested = True
            return
        self.spans.append(Span(kind, start, end))

    def _regex_allowed(self, pos: int) -> bool:
        token = _token_before(self.src, pos)
        if not token:
            return True
        if token[-1].isalnum() or token[-1] in "_$":
            return token in _KEYWORDS_BEFORE_REGEX
        return token not in ")]\"'`"

    def _regex_end(self, pos: int) -> int | None:
        src, n = self.src, len(self.src)
        i, in_class = pos + 1, False
        while i < n:
            char = src[i]
            if char == "\\":
                i += 2
                continue
            if char == "\n":
                return None
            if in_class:
                in_class = char != "]"
            elif char == "[":
                in_class = True
            elif char == "/":
                flags = _REGEX_FLAGS_RE.match(src, i + 1)
                return flags.end() if flags else i + 1
            i += 1
        return None

    def code(self, pos: int, *, until_brace: bool = False) -> int:
        src, n = self.src, len(self.src)
        braces = 0
        while True:
            match = _CODE_STOP_RE.search(src, pos)
            if match is None:
                return n
            i = match.start()
            char = src[i]
            if char in "\"'":
                literal = _STRING_RE[char].match(src, i)
                end = literal.end() if literal else i + 1
                self._opaque("string", i, end)
                pos = end
            elif char == "`":
                if self.depth:
                    self.nested = True
                end = self.template(i)
                self._opaque("template", i, end)
                pos = end
            elif char == "/":
                follower = src[i + 1 : i + 2]
                if follower == "/":
                    end = src.find("\n", i)
                    end = n if end < 0 else end
                    self._opaque("comment", i, end)
                    pos = end
                elif follower == "*":
                    end = src.find("*/", i + 2)
                    end = n if end < 0 else end + 2
                    self._opaque("comment", i, end)
                    pos = end
                elif self._regex_allowed(i) and (end := self._regex_end(i)):
                    self._opaque("regex", i, end)
                    pos = end
                else:
                    pos = i + 1
            elif char == "{":
                braces += 1
                pos = i + 1
            elif until_brace and not braces:
                return i + 1
            else:
                braces = max(braces - 1, 0)
                pos = i + 1

    def template(self, pos: int) -> int:
        src, n = self.src, len(self.src)
        pos += 1
        while True:
            match = _TEMPLATE_STOP_RE.search(src, pos)
            if match is None:
                # an unterminated literal is not something to minify by hand
                self.nested = True
                return n
            token = match.group()
            if token == "`":
                return match.end()
            if token == "${":
                self.depth += 1
                try:
                    pos = self.code(match.end(), until_brace=True)
                finally:
                    self.depth -= 1
            else:
                pos = match.end()


def scan(src: str) -> tuple[list[Span], bool]:
    scanner = _Scanner(src)
    scanner.code(0)
    return scanner.spans, scanner.nested


def has_nested_template_literal(source: str) -> bool:
    # rjsmin reads a template literal as backtick to backtick: a backtick
    # anywhere inside a substitution -- a nested literal, or one inside a
    # string, regex or comment there -- cuts it short and the rest is minified
    # as code
    if "`" not in source or "${" not in source:
        return False
    return scan(source)[1]


def scrub(src: str) -> str:
    spans, _nested = scan(src)
    if not spans:
        return src
    out: list[str] = []
    pos = 0
    for kind, start, end in spans:
        out.append(src[pos:start])
        text = src[start:end]
        if kind == "string":
            if _token_before(src, start) not in _SPECIFIER_KEYWORDS:
                text = text[0] * 2
        elif kind == "comment":
            text = "\n" * text.count("\n") or " "
        else:
            text = '""' if kind == "template" else "/r/"
        out.append(text)
        pos = end
    out.append(src[pos:])
    return "".join(out)
