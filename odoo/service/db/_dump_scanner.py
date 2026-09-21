"""What psql will be made to do by a dump, and what it will not.

A `dump.sql` is restored by feeding it to `psql -f`, and psql interprets
meta-commands -- `\\!`, `\\i`, `\\copy ... from program`, `\\o` -- in the CLIENT,
with the privileges of whoever runs the server process.  A backup from an
untrusted source could carry one.  This module refuses every meta-command but
`\\.`, `\\restrict` and `\\unrestrict`, and refuses a change to
`standard_conforming_strings`, which decides how a quoted string ends and could
otherwise desynchronise the scan from what psql actually parses.

**It does not make the dump's SQL safe, and it is not trying to.**  A restore
executes the dump's SQL with the privileges of the role that connects, so a
dump this module accepts can still do anything that role may do.  Measured
2026-09-21 on a superuser role, which is what `psql -X -q -v ON_ERROR_STOP=1
-f <dump.sql>` connects as in the common deployment:

    COPY pwned FROM PROGRAM 'echo ...'      accepted here, and it runs

`CREATE FUNCTION ... LANGUAGE plpython3u` is the same door, and so are
`ALTER SYSTEM`, `CREATE SERVER` and the rest.  Filtering them one at a time
would make this module's name truer without making it true: arbitrary SQL
cannot be made safe by scanning it, a legitimate Odoo dump may carry
`CREATE EXTENSION`, and a check whose name promises a property it lacks is
worse than no check because the next reader stops looking.

The property that makes a restore safe against a hostile backup is a
**non-superuser restore role** with no `pg_execute_server_program` and no right
to create an untrusted procedural language.  That is a deployment fact, and
`doc/architecture/deployment.md` states it.  `pg_restore` -- the custom-format
path, which this module does not scan -- speaks libpq and has no meta-commands
at all, so it carries exactly this same exposure and no more; its absence here
is consistent rather than a second gap.

`TestTheBoundaryIsAContract` in `tests/service/test_dump_scanner.py` pins both
halves, so the accepting half is a stated contract and not an oversight.
"""

from __future__ import annotations

import logging
import re
import string
from pathlib import Path
from typing import TYPE_CHECKING

from odoo.libs.debug_log import DebugLog

from .._env import get_env_int

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import TextIO

_logger = logging.getLogger("odoo.service.db")
_debug = DebugLog(__name__)


_META_ARG_NONE = r"[ \t]*(?:\r?\n|\Z)"
_META_ARG_KEY = r"[ \t]+[A-Za-z0-9]+[ \t]*(?:\r?\n|\Z)"
_ALLOWED_PSQL_META_COMMANDS: dict[str, re.Pattern[str]] = {
    "\\.": re.compile(_META_ARG_NONE),
    "\\restrict": re.compile(_META_ARG_KEY),
    "\\unrestrict": re.compile(_META_ARG_KEY),
}

_COPY_WORD_MAX_LEN = 5
_CONFORMING_STRINGS = "STANDARD_CONFORMING_STRINGS"
_SQL_WORD_MAX_LEN = len(_CONFORMING_STRINGS)

_IDENT_START_ASCII = frozenset(string.ascii_letters + "_")
_IDENT_CONT_ASCII = frozenset(string.ascii_letters + string.digits + "_$")

# A dollar-quote tag follows the rules of an unquoted identifier except that
# it cannot hold a dollar sign, and an unquoted identifier may hold any
# non-ASCII letter the encoding admits.  An ASCII-only tag pattern left
# `$café$ ... $café$` unrecognised: the body was scanned as SQL, one
# apostrophe in it opened a string that never closed, and the scanner went
# blind to the end of the file while psql closed the tag and ran what came
# after.  The file is read as latin-1, so a multi-byte tag arrives as several
# characters that are each >= \x80 -- which is why the class, not a decoded
# codepoint, is what has to match.
_DOLLAR_TAG_RE = re.compile(
    r"\$(?:[A-Za-z_\x80-\U0010FFFF][A-Za-z0-9_\x80-\U0010FFFF]*)?\$"
)

_DEFAULT_MAX_SCAN_LINE = 64 * 1024 * 1024
_MIN_MAX_SCAN_LINE = 4 * 1024 * 1024


def _is_ident_start(c: str) -> bool:
    return c in _IDENT_START_ASCII or c >= "\x80"


def _is_ident_cont(c: str) -> bool:
    return c in _IDENT_CONT_ASCII or c >= "\x80"


class _PsqlSqlScanner:
    __slots__ = (
        "_ident_run_is_ident",
        "_ident_run_start",
        "_prev_word",
        "_quoted_word",
        "_setting_state",
        "_setting_violation",
        "_stmt_is_copy",
        "_stmt_seen_token",
        "_word",
        "_word_limit",
        "comment_depth",
        "copy_pending",
        "dollar_tag",
        "in_copy_data",
        "in_double_quote",
        "in_single_quote",
        "lineno",
        "single_quote_escaped",
    )

    def __init__(self) -> None:
        self.lineno = 1
        self._word = ""
        self._word_limit = _COPY_WORD_MAX_LEN
        self._setting_state = 0
        self._setting_violation: tuple[int, str] | None = None
        self._quoted_word = ""
        self._prev_word = ""
        self._stmt_seen_token = False
        self._stmt_is_copy = False
        self._ident_run_start = -1
        self._ident_run_is_ident = False
        self.in_copy_data = False
        self.copy_pending = False
        self.comment_depth = 0
        self.dollar_tag: str | None = None
        self.in_single_quote = False
        self.single_quote_escaped = False
        self.in_double_quote = False

    def _resume_carry_over(self, line: str, n: int) -> int:
        if self.comment_depth:
            return self._resume_block_comment(line, 0, n)
        if self.dollar_tag is not None:
            return self._resume_dollar_body(line, 0, n)
        if self.in_single_quote:
            return self._resume_single_quote(line, 0, n)
        if self.in_double_quote:
            return self._resume_double_quote(line, 0, n)
        return 0

    def _consume_copy_data(self, line: str) -> None:
        self.lineno += 1
        if line.rstrip("\n").rstrip("\r") == "\\.":
            self.in_copy_data = False
            self._reset_statement()

    def _absorb_ident_char(self, c: str, i: int) -> None:
        if self._ident_run_start < 0:
            self._ident_run_start = i
            self._ident_run_is_ident = _is_ident_start(c)
            self._word = c
        elif not self._ident_run_is_ident and _is_ident_start(c):
            self._flush_word()
            self._ident_run_start = i
            self._ident_run_is_ident = True
            self._word = c
        elif len(self._word) <= self._word_limit:
            self._word += c

    def _get_meta_command_violation(
        self, line: str, i: int, n: int
    ) -> tuple[int, str] | None:
        word = self._get_command_word(line, i, n)
        arg_pattern = _ALLOWED_PSQL_META_COMMANDS.get(word)
        if arg_pattern is None:
            return (self.lineno, word)
        if not arg_pattern.match(line, i + len(word)):
            end = line.find("\n", i)
            text = line[i:] if end == -1 else line[i:end]
            return (self.lineno, text.rstrip()[:80])
        return None

    def feed(self, line: str) -> tuple[int, str] | None:
        n = len(line)
        self._reset_ident_run()

        if self.in_copy_data:
            self._consume_copy_data(line)
            return self._setting_violation

        i = self._resume_carry_over(line, n)

        while i < n:
            c = line[i]
            if c == "\n":
                self._reset_ident_run()
                self.lineno += 1
                return self._setting_violation

            if c == "-" and i + 1 < n and line[i + 1] == "-":
                i = line.find("\n", i)
                if i == -1:
                    return self._setting_violation
                continue
            if c == "/" and i + 1 < n and line[i + 1] == "*":
                self.comment_depth = 1
                self._reset_ident_run()
                i = self._resume_block_comment(line, i + 2, n)
                continue
            if c == "$" and not self._is_identifier_continued():
                m = _DOLLAR_TAG_RE.match(line, i)
                if m:
                    self.dollar_tag = m.group(0)
                    self._reset_ident_run()
                    self._mark_opaque_token_seen()
                    self._setting_token("")
                    i = self._resume_dollar_body(line, m.end(), n)
                    continue
            if c == "'":
                self.in_single_quote = True
                self._quoted_word = ""
                self.single_quote_escaped = (
                    i > 0 and line[i - 1] in "Ee" and self._ident_run_start == i - 1
                )
                self._reset_ident_run()
                self._mark_opaque_token_seen()
                i = self._resume_single_quote(line, i + 1, n)
                continue
            if c == '"':
                self.in_double_quote = True
                self._quoted_word = ""
                self._reset_ident_run()
                self._mark_opaque_token_seen()
                i = self._resume_double_quote(line, i + 1, n)
                continue
            if c == "\\":
                violation = self._get_meta_command_violation(line, i, n)
                if violation is not None:
                    return violation
                self._reset_ident_run()
                self._mark_opaque_token_seen()
                i = line.find("\n", i)
                if i == -1:
                    return self._setting_violation
                continue

            if _is_ident_cont(c):
                self._absorb_ident_char(c, i)
            else:
                self._reset_ident_run()

            if c == "=":
                self._setting_token(c)
            if c == ";":
                if self.copy_pending:
                    self.copy_pending = False
                    self.in_copy_data = True
                self._reset_statement()
            i += 1
        self._reset_ident_run()
        return self._setting_violation

    def _setting_token(self, token: str, *, quoted: bool = False) -> None:
        """Recognize SET's bounded prefix outside comments and quoted bodies.

        Only explicit true values preserve the lexer's string-escape contract.
        Token state survives physical lines without retaining SQL statements.

        A quoted occurrence of the setting's own name is refused outright,
        whatever the statement around it.  `SET` is not the only way to reach
        the parameter -- `select set_config('standard_conforming_strings',
        'off', false)` changes it for the session, the server reports the
        change, and psql's lexer follows it -- and recognising the call itself
        would mean carrying every function name past this scanner's word
        limit.  pg_dump quotes exactly one setting name, `search_path`, so
        refusing this one costs a legitimate dump nothing.
        """
        word = token.upper()
        if quoted and word == _CONFORMING_STRINGS:
            self._setting_violation = (
                self.lineno,
                "standard_conforming_strings (named by a string literal)",
            )
            return
        state = self._setting_state
        if state == 0:
            self._setting_state = 1 if word == "SET" else -1
        elif state in (1, 2):
            if state == 1 and word in ("LOCAL", "SESSION"):
                self._setting_state = 2
            else:
                self._setting_state = 3 if word == _CONFORMING_STRINGS else -1
        elif state == 3:
            self._setting_state = 4 if word in ("=", "TO") else -1
        elif state == 4:
            if word not in ("ON", "TRUE", "YES", "1"):
                self._setting_violation = (
                    self.lineno,
                    "standard_conforming_strings = " + token[:32],
                )
            self._setting_state = -1
        self._word_limit = (
            _SQL_WORD_MAX_LEN if self._setting_state in (1, 2) else _COPY_WORD_MAX_LEN
        )

    def _is_identifier_continued(self) -> bool:
        return self._ident_run_is_ident

    def _reset_ident_run(self) -> None:
        self._ident_run_start = -1
        self._ident_run_is_ident = False
        self._flush_word()

    def _flush_word(self) -> None:
        word = self._word
        if not word:
            return
        self._word = ""
        if self._setting_state >= 0:
            self._setting_token(word)
        upper = word.upper()
        if not self._stmt_seen_token:
            self._stmt_seen_token = True
            self._stmt_is_copy = upper == "COPY"
        elif self._stmt_is_copy and self._prev_word == "FROM" and upper == "STDIN":
            self.copy_pending = True
        self._prev_word = upper

    def _mark_opaque_token_seen(self) -> None:
        self._stmt_seen_token = True
        self._prev_word = ""

    def _reset_statement(self) -> None:
        self._setting_state = 0
        self._word_limit = _COPY_WORD_MAX_LEN
        self._word = ""
        self._prev_word = ""
        self._stmt_seen_token = False
        self._stmt_is_copy = False

    @staticmethod
    def _get_command_word(line: str, pos: int, n: int) -> str:
        j = pos + 1
        if j < n and line[j] in "!.?\\":
            return line[pos : j + 1]
        k = j
        while k < n and line[k].isalpha():
            k += 1
        return line[pos:k] if k > j else line[pos : pos + 1]

    def _resume_block_comment(self, line: str, i: int, n: int) -> int:
        while i < n and self.comment_depth:
            if line[i] == "\n":
                self.lineno += 1
                i += 1
            elif line.startswith("/*", i):
                self.comment_depth += 1
                i += 2
            elif line.startswith("*/", i):
                self.comment_depth -= 1
                i += 2
            else:
                i += 1
        return i

    def _resume_dollar_body(self, line: str, i: int, n: int) -> int:
        tag = self.dollar_tag
        if tag is None:
            return i
        close = line.find(tag, i)
        if close == -1:
            self.lineno += line.count("\n", i)
            return n
        self.lineno += line.count("\n", i, close)
        self.dollar_tag = None
        return close + len(tag)

    def _resume_single_quote(self, line: str, i: int, n: int) -> int:
        capture = len(self._quoted_word) <= _SQL_WORD_MAX_LEN
        while i < n:
            ch = line[i]
            if capture and ch != "'":
                self._quoted_word += ch
                capture = len(self._quoted_word) <= _SQL_WORD_MAX_LEN
            if ch == "\n":
                self.lineno += 1
                i += 1
            elif ch == "\\" and self.single_quote_escaped:
                i += 2
            elif ch == "'":
                if i + 1 < n and line[i + 1] == "'":
                    i += 2
                else:
                    i += 1
                    self.in_single_quote = False
                    self._setting_token(self._quoted_word, quoted=True)
                    break
            else:
                i += 1
        return i

    def _resume_double_quote(self, line: str, i: int, n: int) -> int:
        capture = len(self._quoted_word) <= _SQL_WORD_MAX_LEN
        while i < n:
            if capture and line[i] != '"':
                self._quoted_word += line[i]
                capture = len(self._quoted_word) <= _SQL_WORD_MAX_LEN
            if line[i] == '"':
                if i + 1 < n and line[i + 1] == '"':
                    i += 2
                else:
                    i += 1
                    self.in_double_quote = False
                    self._setting_token(self._quoted_word, quoted=True)
                    break
            else:
                if line[i] == "\n":
                    self.lineno += 1
                i += 1
        return i


def _iter_physical_lines(text: str) -> Iterator[str]:
    start = 0
    while (idx := text.find("\n", start)) != -1:
        yield text[start : idx + 1]
        start = idx + 1
    if start < len(text):
        yield text[start:]


def _get_disallowed_psql_meta_command(text: str) -> tuple[int, str] | None:
    scanner = _PsqlSqlScanner()
    for line in _iter_physical_lines(text):
        hit = scanner.feed(line)
        if hit is not None:
            return hit
    return None


def _drain_physical_line(fh: TextIO, cap: int) -> None:
    while True:
        part = fh.readline(cap)
        if not part or part.endswith("\n"):
            return


def _refuse_psql_meta_commands(sql_path: str) -> None:
    max_line = get_env_int(
        "ODOO_DUMP_SCAN_MAX_LINE",
        _DEFAULT_MAX_SCAN_LINE,
        minimum=_MIN_MAX_SCAN_LINE,
        logger=_logger,
    )
    scanner = _PsqlSqlScanner()
    hit = None
    with _debug.perf("database.restore.dump_scan", path=sql_path) as span:
        with Path(sql_path).open(encoding="latin-1") as fh:
            while chunk := fh.readline(max_line + 1):
                if len(chunk) > max_line and not chunk.endswith("\n"):
                    if scanner.in_copy_data:
                        _debug.logic(
                            "database.restore.copy_line_drained",
                            lineno=scanner.lineno,
                            max_line=max_line,
                        )
                        _drain_physical_line(fh, max_line + 1)
                        scanner.lineno += 1
                        continue
                    _debug.logic(
                        "database.restore.dump_line_too_long",
                        lineno=scanner.lineno,
                        max_line=max_line,
                    )
                    raise RuntimeError(
                        f"Refusing to restore: the dump's SQL has a line longer than "
                        f"{max_line} characters (at line {scanner.lineno}), which "
                        f"cannot be scanned within a bounded amount of memory. A "
                        f"backup produced by Odoo's own dump has no such line; raise "
                        f"ODOO_DUMP_SCAN_MAX_LINE if this dump is genuinely legitimate."
                    )
                hit = scanner.feed(chunk)
                if hit is not None:
                    break
        span.set(lines=scanner.lineno, refused=hit is not None)
    _debug.logic(
        "database.restore.dump_scanned",
        path=sql_path,
        lines=scanner.lineno,
        max_line=max_line,
        refused=hit is not None,
    )
    if hit is not None:
        lineno, command = hit
        if not command.startswith("\\"):
            raise RuntimeError(
                f"Refusing to restore: the dump's SQL sets {command!r} (line "
                f"{lineno}), which changes how a quoted string is escaped and "
                f"can desynchronize this scanner from what psql actually runs. "
                f"A backup produced by Odoo's own dump never needs this setting."
            )
        raise RuntimeError(
            f"Refusing to restore: the dump's SQL contains the psql "
            f"meta-command {command!r} (line {lineno}), which would run with "
            f"this server's OS/database privileges. A backup produced by Odoo's "
            f"own dump contains no such command; the only permitted forms are "
            f"``\\restrict <key>`` / ``\\unrestrict <key>`` with an alphanumeric "
            f"key, and the ``\\.`` COPY terminator alone on its line."
        )


__all__ = (
    "_PsqlSqlScanner",
    "_get_disallowed_psql_meta_command",
    "_iter_physical_lines",
    "_refuse_psql_meta_commands",
)
