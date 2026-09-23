import ast
import os
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import odoo.modules
from odoo import api
from odoo.api import Environment
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

VERSION = 1
DEFAULT_EXCLUDE = [
    "__manifest__.py",
    "tests/**/*",
    "static/lib/**/*",
    "static/tests/**/*",
    "migrations/**/*",
    "upgrades/**/*",
]

STANDARD_MODULES = ["web", "test_themes", "base"]
MAX_FILE_SIZE = 25 * 2**20
MAX_LINE_SIZE = 100000
VALID_EXTENSION = [".py", ".js", ".xml", ".css", ".scss"]

_JS_CODE_RUN = re.compile(r"[^/'\"`{}]+")
_JS_STRING = re.compile(r"'(?:\\.|[^\\'\n])*'?|\"(?:\\.|[^\\\"\n])*\"?", re.DOTALL)
_JS_TEMPLATE_CHUNK = re.compile(r"(?:\\.|[^\\`$]|\$(?!\{))*(`|\$\{|\Z)", re.DOTALL)
_JS_REGEX_LITERAL = re.compile(
    r"/(?![*/])(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^/\\\n\[])+/[A-Za-z]*"
)
_JS_OPERAND_END = re.compile(r"(?:[\w$)\]]|\+\+|--)\Z")
_JS_KEYWORD_END = re.compile(
    r"(?<![\w$.])(?:return|typeof|instanceof|in|of|new|delete|void|throw|case"
    r"|do|else|yield|await)\Z"
)


def _strip_js_comments(s: str) -> str:
    # A quoted string ends at the newline JavaScript rejects it at, so a
    # misread slash (regex or division) can never run past its own line.
    out: list[str] = []
    template_braces: list[int] = []
    pos, end = 0, len(s)
    regex_allowed = True
    in_template = False
    while pos < end:
        if in_template:
            match = _JS_TEMPLATE_CHUNK.match(s, pos)
            assert match is not None
            out.append(match.group(0))
            pos = match.end()
            if match.group(1) == "${":
                template_braces.append(0)
                regex_allowed = True
            else:
                regex_allowed = False
            in_template = False
            continue
        char = s[pos]
        if char == "/":
            if s.startswith("//", pos):
                newline = s.find("\n", pos)
                pos = end if newline < 0 else newline
                out.append(" ")
            elif s.startswith("/*", pos):
                close = s.find("*/", pos + 2)
                pos = end if close < 0 else close + 2
                out.append(" ")
            elif regex_allowed and (match := _JS_REGEX_LITERAL.match(s, pos)):
                out.append(match.group(0))
                pos = match.end()
                regex_allowed = False
            else:
                out.append(char)
                pos += 1
                regex_allowed = True
        elif char in "'\"":
            match = _JS_STRING.match(s, pos)
            assert match is not None
            out.append(match.group(0))
            pos = match.end()
            regex_allowed = False
        elif char == "`":
            out.append(char)
            pos += 1
            in_template = True
        elif char == "{":
            if template_braces:
                template_braces[-1] += 1
            out.append(char)
            pos += 1
            regex_allowed = True
        elif char == "}":
            out.append(char)
            pos += 1
            if template_braces and not template_braces[-1]:
                template_braces.pop()
                in_template = True
            else:
                if template_braces:
                    template_braces[-1] -= 1
                regex_allowed = True
        else:
            match = _JS_CODE_RUN.match(s, pos)
            assert match is not None
            run = match.group(0)
            out.append(run)
            pos = match.end()
            if tail := run.rstrip():
                regex_allowed = bool(
                    _JS_KEYWORD_END.search(tail) or not _JS_OPERAND_END.search(tail)
                )
    return "".join(out)


class Cloc:
    def __init__(self) -> None:
        self.modules: dict[str, dict[str, tuple[int, int] | tuple[int, str]]] = {}
        self.code: dict[str, int] = {}
        self.total: dict[str, int] = {}
        self.errors: dict[str, dict[str, Any]] = {}
        self.excluded: dict[str, dict[str, tuple[int, int] | tuple[int, str]]] = {}
        self.max_width: int = 70

    def parse_xml(self, s: str) -> tuple[int, int]:
        s = s.strip() + "\n"
        total = s.count("\n")
        s = re.sub(r"(<!--.*?-->)", "", s, flags=re.DOTALL)
        s = re.sub(r"\s*\n\s*", r"\n", s).lstrip()
        return s.count("\n"), total

    def parse_py(self, s: str) -> tuple[int, int] | tuple[int, str]:
        try:
            s = s.strip() + "\n"
            total = s.count("\n")
            lines = set()
            for i in ast.walk(ast.parse(s)):
                if hasattr(i, "lineno"):
                    lines.add(i.lineno)
            return len(lines), total
        except Exception:
            return (-1, "Syntax Error")

    def _count_code_lines(
        self, s: str, strip_comments: Callable[[str], str]
    ) -> tuple[int, int] | tuple[int, str]:
        s = s.strip() + "\n"
        total = s.count("\n")
        if max(len(l) for l in s.split("\n")) > MAX_LINE_SIZE:
            return -1, "Max line size exceeded"
        s = strip_comments(s)
        s = re.sub(r"\s*\n\s*", r"\n", s).lstrip()
        return s.count("\n"), total

    def parse_c_like(self, s: str, regex: str) -> tuple[int, int] | tuple[int, str]:
        def replacer(match: re.Match) -> str:
            s = match.group(0)
            return " " if s.startswith("/") else s

        comments_re = re.compile(regex, re.DOTALL | re.MULTILINE)
        return self._count_code_lines(s, lambda text: comments_re.sub(replacer, text))

    def parse_js(self, s: str) -> tuple[int, int] | tuple[int, str]:
        return self._count_code_lines(s, _strip_js_comments)

    def parse_scss(self, s: str) -> tuple[int, int] | tuple[int, str]:
        return self.parse_c_like(
            s, r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"'
        )

    def parse_css(self, s: str) -> tuple[int, int] | tuple[int, str]:
        return self.parse_c_like(s, r'/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"')

    def parse(self, s: str, ext: str) -> tuple[int, int] | tuple[int, str] | None:
        if ext == ".py":
            return self.parse_py(s)
        elif ext == ".js":
            return self.parse_js(s)
        elif ext == ".xml":
            return self.parse_xml(s)
        elif ext == ".css":
            return self.parse_css(s)
        elif ext == ".scss":
            return self.parse_scss(s)
        return None

    def book(
        self,
        module: str,
        item: str = "",
        count: tuple[int, int] | tuple[int, str] = (0, 0),
        exclude: bool = False,
    ) -> None:
        if count[0] == -1:
            self.errors.setdefault(module, {})
            self.errors[module][item] = count[1]
        elif exclude and item:
            self.excluded.setdefault(module, {})
            self.excluded[module][item] = count
        else:
            self.modules.setdefault(module, {})
            if item:
                self.modules[module][item] = count
            self.code[module] = self.code.get(module, 0) + count[0]
            total = count[1]
            if isinstance(total, int):
                self.total[module] = self.total.get(module, 0) + total
            self.max_width = max(self.max_width, len(module), len(item) + 4)

    def count_path(self, path: str, exclude: set[str] | None = None) -> None:
        path = path.rstrip("/")
        exclude_list = []
        for i in odoo.modules.module.MANIFEST_NAMES:
            manifest_path = Path(path, i)
            try:
                manifest = manifest_path.read_bytes()
            except OSError:
                continue
            try:
                declared = ast.literal_eval(manifest.decode("utf-8"))
            except (ValueError, SyntaxError, UnicodeDecodeError) as exc:
                self.book(
                    Path(path).name,
                    i,
                    (-1, f"Manifest is not a literal, exclusions ignored: {exc}"),
                )
                _debug.logic(
                    "cloc.manifest_unparsable",
                    module=Path(path).name,
                    error=type(exc).__name__,
                )
                declared = {}
            exclude_list.extend(DEFAULT_EXCLUDE)
            if isinstance(declared, dict):
                for j in ["cloc_exclude", "demo", "demo_xml"]:
                    patterns = declared.get(j) or []
                    exclude_list.extend(
                        [patterns] if isinstance(patterns, str) else patterns
                    )
            break
        module_name = Path(path).name
        exclude = set(exclude or ())
        for i in filter(None, exclude_list):
            if isinstance(i, str) and ".." in i:
                raise ValueError(
                    f"Invalid exclusion path {i!r}: '..' is not allowed. "
                    "Use a normalized path."
                )
            try:
                exclude.update(str(p) for p in Path(path).glob(i))
            except (NotImplementedError, ValueError, TypeError) as exc:
                self.book(
                    module_name,
                    f"exclusion {i!r}",
                    (-1, f"Invalid exclusion pattern, ignored: {exc}"),
                )
                _debug.logic(
                    "cloc.exclusion_invalid", module=module_name, pattern=repr(i)
                )

        self.book(module_name)
        counted = excluded = 0  # debuglog
        with _debug.perf(
            "cloc.module_counted", module=module_name, exclusions=len(exclude)
        ) as span:
            for root, _dirs, files in os.walk(path):
                for file_name in files:
                    file_path = str(Path(root, file_name))

                    if file_path in exclude:
                        excluded += 1  # debuglog
                        continue

                    ext = Path(file_path).suffix.lower()
                    if ext not in VALID_EXTENSION:
                        continue

                    if Path(file_path).stat().st_size > MAX_FILE_SIZE:
                        self.book(
                            module_name, file_path, (-1, "Max file size exceeded")
                        )
                        _debug.logic("cloc.file_too_large", file=file_path)
                        continue

                    content = Path(file_path).read_bytes().decode("latin1")
                    if (parsed := self.parse(content, ext)) is not None:
                        self.book(module_name, file_path, parsed)
                        counted += 1  # debuglog
            span.set(
                files=counted,
                excluded=excluded,
                code=self.code.get(module_name, 0),
                errors=len(self.errors.get(module_name, {})),
            )

    def count_modules(self, env: Environment) -> None:
        exclude_path = {
            m.addons_path
            for name in STANDARD_MODULES
            if (m := odoo.modules.Manifest.for_addon(name, display_warning=False))
        }

        domain: list[tuple[str, str, Any]] = [("state", "=", "installed")]
        if env["ir.module.module"]._fields.get("imported"):
            domain.append(("imported", "=", False))
        module_list = env["ir.module.module"].search(domain).mapped("name")

        skipped = 0  # debuglog
        for module_name in module_list:
            manifest = odoo.modules.Manifest.for_addon(module_name)
            if manifest and manifest.addons_path not in exclude_path:
                self.count_path(manifest.path)
            else:
                skipped += 1  # debuglog
        _debug.pipeline(
            "cloc.modules_counted",
            installed=len(module_list),
            skipped=skipped,
            standard_paths=len(exclude_path),
        )

    def _count_custom_server_actions(self, env: Environment) -> None:
        imported_module_sa = ""
        if env["ir.module.module"]._fields.get("imported"):
            imported_module_sa = "OR (m.imported = TRUE AND m.state = 'installed')"
        query = f"""
                SELECT s.id, min(m.name), array_agg(d.module)
                  FROM ir_act_server AS s
             LEFT JOIN ir_model_data AS d
                    ON (d.res_id = s.id AND d.model = 'ir.actions.server')
             LEFT JOIN ir_module_module AS m
                    ON m.name = d.module
                 WHERE s.state = 'code' AND (m.name IS null {imported_module_sa})
              GROUP BY s.id
        """
        env.cr.execute(query)
        data = {r[0]: (r[1], r[2]) for r in env.cr.fetchall()}
        server_actions: Any = env["ir.actions.server"]
        for a in server_actions.browse(data.keys()):
            self.book(
                data[a.id][0] or "odoo/studio",
                f"ir.actions.server/{a.id}: {a.name}",
                self.parse_py(a.code),
                "__cloc_exclude__" in data[a.id][1],
            )

    def _count_custom_computed_fields(self, env: Environment) -> None:
        imported_module_field = ("'odoo/studio'", "")
        if env["ir.module.module"]._fields.get("imported"):
            imported_module_field = (
                "min(m.name)",
                "AND m.imported = TRUE AND m.state = 'installed'",
            )
        query = r"""
                SELECT f.id, f.name, {}, array_agg(d.module)
                  FROM ir_model_fields AS f
             LEFT JOIN ir_model_data AS d ON (d.res_id = f.id AND d.model = 'ir.model.fields')
             LEFT JOIN ir_module_module AS m ON m.name = d.module {}
                 WHERE f.compute IS NOT null AND f.state = 'manual'
              GROUP BY f.id, f.name
        """.format(*imported_module_field)
        env.cr.execute(query)
        data = {
            r[0]: (r[2], r[3])
            for r in env.cr.fetchall()
            if not ("studio_customization" in r[3] and not r[1].startswith("x_studio"))
        }
        for f in env["ir.model.fields"].browse(data.keys()):
            self.book(
                data[f.id][0] or "odoo/studio",
                f"ir.model.fields/{f.id}: {f.name}",
                self.parse_py(f.compute),
                "__cloc_exclude__" in data[f.id][1],
            )

    def _count_imported_qweb_views(self, env: Environment) -> None:
        query = """
            SELECT view.id, min(mod.name), array_agg(data.module)
              FROM ir_ui_view view
        INNER JOIN ir_model_data data ON view.id = data.res_id AND data.model = 'ir.ui.view'
         LEFT JOIN ir_module_module mod ON mod.name = data.module AND mod.imported = True
             WHERE view.type = 'qweb' AND data.module != 'studio_customization'
          GROUP BY view.id
            HAVING count(mod.name) > 0
        """
        env.cr.execute(query)
        custom_views = {r[0]: (r[1], r[2]) for r in env.cr.fetchall()}
        for view in env["ir.ui.view"].browse(custom_views.keys()):
            module_name = custom_views[view.id][0]
            self.book(
                module_name,
                f"/{module_name}/views/{view.name}.xml",
                self.parse_xml(view.arch_base),
                "__cloc_exclude__" in custom_views[view.id][1],
            )

    def _count_imported_attachments(self, env: Environment) -> None:
        query = r"""
            SELECT attach.id, min(mod.name), array_agg(data.module)
              FROM ir_attachment attach
        INNER JOIN ir_model_data data ON attach.id = data.res_id AND data.model = 'ir.attachment'
         LEFT JOIN ir_module_module mod ON mod.name = data.module AND mod.imported = True
             WHERE attach.name ~ '.*\.(js|xml|css|scss)$'
          GROUP BY attach.id
            HAVING count(mod.name) > 0
        """
        env.cr.execute(query)
        uploaded_file = {r[0]: (r[1], r[2]) for r in env.cr.fetchall()}
        for attach in env["ir.attachment"].browse(uploaded_file.keys()):
            module_name = uploaded_file[attach.id][0]
            if not attach.url:
                continue
            ext = Path(attach.url).suffix.lower()
            if ext not in VALID_EXTENSION:
                continue

            if attach.file_size > MAX_FILE_SIZE:
                self.book(module_name, attach.url, (-1, "Max file size exceeded"))
                continue

            parsed = self.parse(attach.raw.decode("latin1"), ext)
            if parsed is not None:
                self.book(
                    module_name,
                    attach.url,
                    parsed,
                    "__cloc_exclude__" in uploaded_file[attach.id][1],
                )

    def count_customization(self, env: Environment) -> None:
        with _debug.perf("cloc.customization_counted", cr=env.cr) as span:
            self._count_custom_server_actions(env)
            self._count_custom_computed_fields(env)

            imported = bool(env["ir.module.module"]._fields.get("imported"))
            span.set(imported_modules=imported)
            if not imported:
                return

            self._count_imported_qweb_views(env)
            self._count_imported_attachments(env)

    def count_env(self, env: Environment) -> None:
        self.count_modules(env)
        self.count_customization(env)

    def count_database(self, database: str) -> None:
        registry = odoo.modules.registry.Registry(database)
        with registry.cursor() as cr:
            uid = api.SUPERUSER_ID
            env = api.Environment(cr, uid, {})
            self.count_env(env)

    def report(self, verbose: bool = False, width: int | None = None) -> str:
        if not width:
            width = min(self.max_width, shutil.get_terminal_size()[0] - 24)
        hr = "-" * (width + 24) + "\n"
        fmt = f"{{k:{width}}}{{lines:>8}}{{other:>8}}{{code:>8}}\n"

        s = fmt.format(k="Odoo cloc", lines="Line", other="Other", code="Code")
        s += hr
        for m in sorted(self.modules):
            s += fmt.format(
                k=m,
                lines=self.total[m],
                other=self.total[m] - self.code[m],
                code=self.code[m],
            )
            if verbose:
                for i in sorted(
                    self.modules[m],
                    key=lambda i: self.modules[m][i][0],
                    reverse=True,
                ):
                    code, total = self.modules[m][i]
                    if not isinstance(total, int):
                        continue
                    s += fmt.format(
                        k="    " + i, lines=total, other=total - code, code=code
                    )
        s += hr
        total = sum(self.total.values())
        code = sum(self.code.values())
        s += fmt.format(k="", lines=total, other=total - code, code=code)

        if self.excluded and verbose:
            ex = fmt.format(k="Excluded", lines="Line", other="Other", code="Code")
            ex += hr
            for m in sorted(self.excluded):
                for i in sorted(
                    self.excluded[m],
                    key=lambda i: self.excluded[m][i][0],
                    reverse=True,
                ):
                    code, total = self.excluded[m][i]
                    if not isinstance(total, int):
                        continue
                    ex += fmt.format(
                        k="    " + i, lines=total, other=total - code, code=code
                    )
            ex += hr
            s += ex

        if self.errors:
            e = "\nErrors\n\n"
            for m in sorted(self.errors):
                e += f"{m}\n"
                for i in sorted(self.errors[m]):
                    e += fmt.format(
                        k="    " + i, lines=self.errors[m][i], other="", code=""
                    )
            s += e

        return s
