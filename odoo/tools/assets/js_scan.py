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

    def run(self) -> None:
        # an explicit stack, not recursion: a source nesting substitutions
        # deeper than the interpreter's recursion limit is still scanned
        src, n = self.src, len(self.src)
        code_frames: list[int] = [0]
        template_starts: list[int] = []
        in_template: list[bool] = [False]
        pos = 0
        while in_template:
            if in_template[-1]:
                match = _TEMPLATE_STOP_RE.search(src, pos)
                if match is None:
                    # an unterminated literal is not something to minify by hand
                    self.nested = True
                    pos = n
                elif (token := match.group()) == "${":
                    self.depth += 1
                    code_frames.append(0)
                    in_template.append(False)
                    pos = match.end()
                    continue
                elif token != "`":
                    pos = match.end()
                    continue
                else:
                    pos = match.end()
                in_template.pop()
                self._opaque("template", template_starts.pop(), pos)
                continue
            match = _CODE_STOP_RE.search(src, pos)
            if match is None:
                pos = n
                self._close_code_frame(code_frames, in_template)
                continue
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
                template_starts.append(i)
                in_template.append(True)
                pos = i + 1
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
                code_frames[-1] += 1
                pos = i + 1
            elif len(in_template) > 1 and not code_frames[-1]:
                pos = i + 1
                self._close_code_frame(code_frames, in_template)
            else:
                code_frames[-1] = max(code_frames[-1] - 1, 0)
                pos = i + 1

    def _close_code_frame(
        self, code_frames: list[int], in_template: list[bool]
    ) -> None:
        code_frames.pop()
        in_template.pop()
        if in_template:
            self.depth -= 1


def scan(src: str) -> tuple[list[Span], bool]:
    scanner = _Scanner(src)
    scanner.run()
    return scanner.spans, scanner.nested


# rjsmin (1.2) knows a regex only after punctuation or `return`; after any
# other keyword it reads the slash as division and minifies the body as code
_KEYWORDS_RJSMIN_MISREADS = _KEYWORDS_BEFORE_REGEX - {"return"}
_KEYWORD_THEN_SLASH_RE = re.compile(
    r"\b(?:%s)\s*/(?![/*])" % "|".join(sorted(_KEYWORDS_RJSMIN_MISREADS))
)


def rjsmin_misreads(source: str) -> bool:
    # rjsmin reads a template literal as backtick to backtick: a backtick
    # anywhere inside a substitution -- a nested literal, or one inside a
    # string, regex or comment there -- cuts it short and the rest is minified
    # as code. It also collapses the body of a regex that follows a keyword it
    # does not know (`typeof /a  b/` becomes `typeof/a b/`)
    templates = "`" in source and "${" in source
    keyword_regex = bool(_KEYWORD_THEN_SLASH_RE.search(source))
    if not (templates or keyword_regex):
        return False
    spans, nested = scan(source)
    return nested or any(
        kind == "regex" and _token_before(source, start) in _KEYWORDS_RJSMIN_MISREADS
        for kind, start, _end in spans
    )


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
