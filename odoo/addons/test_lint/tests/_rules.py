import ast
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass

from . import (
    _checker_batch,
    _checker_company_config,
    _checker_config_patch,
    _checker_credential_storage,
    _checker_egress,
    _checker_field_declaration,
    _checker_gettext,
    _checker_http_json,
    _checker_noqa_rationale,
    _checker_onchange,
    _checker_orm_import,
    _checker_receiver,
    _checker_row_counter,
    _checker_shadowed_def,
    _checker_sql,
    _checker_tax_company,
    _checker_unlink,
)


@dataclass(frozen=True, slots=True)
class Finding:
    path: str
    lineno: int
    rule: str
    message: str = ""
    col_offset: int = 0

    def __str__(self) -> str:
        tail = f" {self.message}" if self.message else ""
        return f"{self.path}:{self.lineno}:{self.col_offset} [{self.rule}]{tail}"

    @property
    def sort_key(self) -> tuple[str, int, int, str]:
        return (self.path, self.lineno, self.col_offset, self.rule)


@dataclass(frozen=True, slots=True)
class Source:
    path: str
    in_module: bool


@dataclass(frozen=True, slots=True)
class Unit:
    path: str
    source: str
    tree: ast.Module
    nodes: list[ast.AST]
    in_module: bool
    is_test: bool = False
    comments: dict[int, str] | None = None


def is_test_path(path: str) -> bool:
    return any(part == "tests" or part.startswith("test_") for part in path.split("/"))


_COMPOUND = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.If,
    ast.Try,
    ast.With,
    ast.AsyncWith,
    ast.Match,
)


def statement_spans(nodes: list[ast.AST]) -> dict[int, int]:
    spans: dict[int, int] = {}
    for node in nodes:
        start = getattr(node, "lineno", None)
        end = getattr(node, "end_lineno", None)
        if start is None or end is None or isinstance(node, _COMPOUND):
            continue
        if end > spans.get(start, start):
            spans[start] = end
    return spans


def directive_lines(spans: dict[int, int], lineno: int) -> set[int]:
    lines = {lineno}
    for start, end in spans.items():
        if start <= lineno <= end:
            lines.update(range(start, end + 1))
    return lines


def walk_with_parents(tree: ast.AST) -> list[ast.AST]:
    nodes: list[ast.AST] = []
    stack: list[ast.AST] = [tree]
    while stack:
        node = stack.pop()
        nodes.append(node)
        children = list(ast.iter_child_nodes(node))
        for child in children:
            child._parent = node
        stack.extend(reversed(children))
    return nodes


@dataclass(frozen=True, slots=True)
class Rule:
    name: str
    code: str
    advice: str

    @property
    def gate(self) -> str:
        return "lint_" + self.name.replace("-", "_")

    @property
    def aliases(self) -> frozenset[str]:
        return frozenset({self.name, self.code}) - {""}


RULES: tuple[Rule, ...] = (
    Rule(
        "sql-injection",
        "E8501",
        "build the query with `SQL()` so the value is passed as a parameter, or "
        "add `# noqa: E8501  <why this one is safe>`",
    ),
    Rule(
        "gettext-variable",
        "E8502",
        "_() takes a literal; a variable cannot be extracted into the .pot",
    ),
    Rule(
        "gettext-placeholders",
        "E8503",
        "use %(name)s rather than a second bare %s, so a translator can reorder them",
    ),
    Rule(
        "gettext-repr",
        "E8504",
        "%r leaks Python syntax into a user-facing sentence",
    ),
    Rule(
        "missing-gettext",
        "E8505",
        "wrap the message in _() so it can be translated",
    ),
    Rule(
        "raise-unlink-override",
        "E8506",
        "use @api.ondelete(at_uninstall=False): raising in unlink also blocks "
        "uninstalling the module",
    ),
    Rule(
        "n-plus-one-query",
        "E8507",
        "hoist the query out of the loop and index the result in memory",
    ),
    Rule(
        "company-field-outside-config",
        "E8530",
        "declare the field on the application's mixin.company.config model and "
        "link it from res.company through one <app>_config_id field",
    ),
    Rule(
        "tax-company-singular",
        "E8514",
        "account.tax has company_ids, not company_id: use "
        "`filtered_domain(env['account.tax']._check_company_domain(company))`",
    ),
    Rule(
        "http-json-string",
        "E8515",
        'a type="http" route answering JSON must say so: return '
        "request.prepare_json_response(payload); a bare json.dumps string goes "
        "out as text/html and the client's post()/get() helpers refuse to parse it",
    ),
    Rule(
        "orm-import",
        "E8508",
        "reach the ORM through odoo.api / odoo.fields / odoo.models",
    ),
    Rule(
        "onchange-domain",
        "E8509",
        "put the domain on the field, so every reader of it agrees rather than "
        "just this one form view",
    ),
    Rule(
        "config-chainmap-patch",
        "E8510",
        "use config.patch(**values); patch.dict on the options ChainMap flattens "
        "every lower layer into _override_options and the damage lands on the "
        "next test",
    ),
    Rule(
        "gettext-developer-error",
        "E8511",
        "drop the `_()` and use an f-string: a builtin exception reaches a reader "
        "as a traceback, and translating it books a developer diagnostic into the "
        "module catalogue",
    ),
    Rule(
        "shadowed-definition",
        "E8513",
        "define the member once: Python keeps the last definition, so the earlier "
        "one is dead code that still reads as live",
    ),
    Rule(
        "unique-over-translated-column",
        "E8512",
        "a translated column is jsonb, so UNIQUE over it compares whole "
        "translation documents and stops matching as soon as one row carries a "
        "language the other does not -- declare name_uniq_index(...) from "
        "odoo/addons/base/models/catalog_mixin.py instead, which indexes the "
        "source term",
    ),
    Rule(
        "null-exempt-composite-unique",
        "E8517",
        "a composite UNIQUE naming a column that may be NULL enforces nothing on "
        "the rows where it is empty, because PostgreSQL counts NULLs as distinct "
        "-- say NULLS NOT DISTINCT if the key must hold there, or make the "
        "exemption explicit with a partial WHERE <column> IS NOT NULL",
    ),
    Rule(
        "row-counter-in-test",
        "E8516",
        "read cr.sql_statement_count: sql_log_count is incremented by the ROW "
        "count (odoo/db/metrics.py) so a correctly batched insert of N rows "
        "scores N, and a per-record budget measured with it has headroom "
        "proportional to the rows each record writes",
    ),
    Rule(
        "raw-egress",
        "E8518",
        "send the call through `env['ir.egress']` (a configured vendor through "
        "integration's `get_api_client(env, code)`, which builds on it), so the "
        "address is checked, the connection pinned, every redirect checked again "
        "and the response capped; a vendor SDK that cannot take the session takes "
        "`# noqa: E8518  <why it cannot>`",
    ),
    Rule(
        "receiver-fail-open",
        "E8528",
        "resolve the caller through an inbound gate before doing anything: "
        "`InboundController.inspect_inbound_request`, or the receiver's "
        "`_check_inbound_request`, so an unknown caller is refused, a flood is "
        "throttled and every refusal is recorded; a route that must stay open "
        "takes `# noqa: E8528  <why>`",
    ),
    Rule(
        "secret-in-environ",
        "E8519",
        "hand the secret to the child process in its own `env=` mapping: "
        "os.environ belongs to the whole worker, so every later subprocess and "
        "every other company's work inherits it",
    ),
    Rule(
        "credential-storage",
        "E8520",
        "keep the secret in credential.credential and hold a Many2one to it, "
        "with a computed field of the old name reading it through the vault's use "
        "path; a plain column or an ir.config_parameter is in every backup in "
        "clear",
    ),
    Rule(
        "field-redeclared",
        "E8521",
        "declare the field once: the class body keeps the last assignment, so "
        "the earlier declaration is dead while it still reads as the one in force",
    ),
    Rule(
        "default-evaluated-at-import",
        "E8522",
        "pass the callable (default=fields.Date.today), not its result: a call in "
        "the declaration runs once when the module is imported, and every record "
        "created afterwards gets that same value",
    ),
    Rule(
        "selection-duplicate-key",
        "E8523",
        "give each selection key one label: Selection stores the list as a dict, "
        "so the last label wins and the others are dead",
    ),
    Rule(
        "field-hook-prefix",
        "E8524",
        "name the hook for its family -- _compute_*, _inverse_*, _search_*, "
        "_selection_* -- so a reader and the naming gates can tell a field hook "
        "from a helper (coding_guidelines.rst 2.4.1)",
    ),
    Rule(
        "field-positional-argument",
        "E8525",
        "spell every argument as its keyword: a positional label, comodel or "
        "selection reads as a bare string and only the signature says which",
    ),
    Rule(
        "field-attribute-order",
        "E8526",
        "keywords in FIELD_ATTRIBUTE_ORDER, one per line once there are two: "
        "what the field is, what it says, its shape, how its value is produced, "
        "how it is stored, what it points at, who tracks it, then groups= and "
        "help= last -- run _sort_field_attributes.py",
    ),
    Rule(
        "dead-field-attribute",
        "E8527",
        "drop the attribute: index= without a column, precompute= without "
        "store=True and compute= beside related= are ignored at setup",
    ),
    Rule(
        "stored-related",
        "E8529",
        "drop store=True: a related field over many2one hops filters, groups, "
        "sorts and aggregates through the join. A copy that carries a composite "
        "index or a UNIQUE stays, with `# noqa: E8529  <what needs the column>`",
    ),
    Rule(
        "noqa-rationale",
        "",
        "write the reason after the codes: `# noqa: F401  re-exported by __init__`",
    ),
    Rule(
        "unreadable-source",
        "",
        "the scan could not parse or tokenise this file, so every other rule "
        "silently skipped it; fix the file or take it out of the corpus",
    ),
)

BY_NAME: dict[str, Rule] = {rule.name: rule for rule in RULES}

ALIASES: dict[str, frozenset[str]] = {
    rule.name: frozenset(alias.lower() for alias in rule.aliases) for rule in RULES
}

UNSUPPRESSABLE = frozenset({"noqa-rationale", "unreadable-source"})


def _sql(unit: Unit) -> Iterator[object]:
    return _checker_sql.SqlInjectionChecker(unit.path).check_nodes(unit.nodes)


def _gettext(unit: Unit) -> Iterable[object]:
    return _checker_gettext.check(unit.tree, unit.nodes)


def _unlink(unit: Unit) -> Iterable[object]:
    return _checker_unlink.check(unit.tree, unit.nodes)


def _batch(unit: Unit) -> Iterable[object]:
    return _checker_batch.check(unit.tree, unit.nodes)


def _noqa_rationale(unit: Unit) -> Iterable[object]:
    return _checker_noqa_rationale.find_violations(unit.comments or {})


def _orm_import(unit: Unit) -> Iterable[object]:
    return _checker_orm_import.check(unit.tree, unit.nodes)


def _onchange(unit: Unit) -> Iterable[object]:
    return _checker_onchange.check(unit.tree, unit.nodes)


def _row_counter(unit: Unit) -> Iterable[object]:
    return _checker_row_counter.check(unit.tree, unit.nodes)


def _config_patch(unit: Unit) -> Iterable[object]:
    return _checker_config_patch.check(unit.tree, unit.nodes)


def _shadowed_def(unit: Unit) -> Iterable[object]:
    return _checker_shadowed_def.check(unit.tree, unit.nodes)


def _tax_company(unit: Unit) -> Iterable[object]:
    return _checker_tax_company.check(unit.tree, unit.nodes)


def _company_config(unit: Unit) -> Iterable[object]:
    if "/addons/base/" in unit.path:
        return ()
    return _checker_company_config.check(unit.tree)


def _http_json(unit: Unit) -> Iterable[object]:
    return _checker_http_json.check(unit.tree, unit.nodes)


def _raw_egress(unit: Unit) -> Iterable[object]:
    return _checker_egress.check_raw_egress(unit.tree, unit.nodes)


def _receiver_fail_open(unit: Unit) -> Iterable[object]:
    return _checker_receiver.check(unit.tree)


def _secret_in_environ(unit: Unit) -> Iterable[object]:
    return _checker_egress.check_secret_in_environ(unit.tree, unit.nodes)


def _field_declaration(unit: Unit) -> Iterable[object]:
    return _checker_field_declaration.check(unit.tree, unit.nodes)


def _credential_storage(unit: Unit) -> Iterable[object]:
    return _checker_credential_storage.check(unit.tree, unit.path)


def _anywhere(unit: Unit) -> bool:
    return True


def _outside_tests(unit: Unit) -> bool:
    return not unit.is_test


def _in_an_addon_outside_tests(unit: Unit) -> bool:
    return unit.in_module and not unit.is_test


def _in_an_addon(unit: Unit) -> bool:
    return unit.in_module


def _in_tests(unit: Unit) -> bool:
    return unit.is_test


@dataclass(frozen=True, slots=True)
class Checker:
    run: Callable[[Unit], Iterable]
    applies_to: Callable[[Unit], bool]
    rules: frozenset[str]

    @property
    def rule(self) -> str | None:
        return next(iter(self.rules)) if len(self.rules) == 1 else None


CHECKERS: tuple[Checker, ...] = (
    Checker(_sql, _outside_tests, frozenset({"sql-injection"})),
    Checker(
        _gettext,
        _outside_tests,
        frozenset(
            {
                "gettext-variable",
                "gettext-placeholders",
                "gettext-repr",
                "missing-gettext",
                "gettext-developer-error",
            }
        ),
    ),
    Checker(_unlink, _anywhere, frozenset({"raise-unlink-override"})),
    Checker(_batch, _outside_tests, frozenset({"n-plus-one-query"})),
    Checker(_noqa_rationale, _anywhere, frozenset({"noqa-rationale"})),
    Checker(_orm_import, _in_an_addon_outside_tests, frozenset({"orm-import"})),
    Checker(_onchange, _in_an_addon, frozenset({"onchange-domain"})),
    Checker(_config_patch, _anywhere, frozenset({"config-chainmap-patch"})),
    Checker(_shadowed_def, _anywhere, frozenset({"shadowed-definition"})),
    Checker(_tax_company, _anywhere, frozenset({"tax-company-singular"})),
    Checker(
        _company_config,
        _in_an_addon_outside_tests,
        frozenset({"company-field-outside-config"}),
    ),
    Checker(_http_json, _in_an_addon_outside_tests, frozenset({"http-json-string"})),
    Checker(_row_counter, _in_tests, frozenset({"row-counter-in-test"})),
    Checker(
        _raw_egress,
        _in_an_addon_outside_tests,
        frozenset({"raw-egress"}),
    ),
    Checker(_secret_in_environ, _outside_tests, frozenset({"secret-in-environ"})),
    Checker(
        _receiver_fail_open,
        _in_an_addon_outside_tests,
        frozenset({"receiver-fail-open"}),
    ),
    Checker(
        _credential_storage,
        _in_an_addon_outside_tests,
        frozenset({"credential-storage"}),
    ),
    Checker(
        _field_declaration,
        _outside_tests,
        frozenset(
            {
                "field-redeclared",
                "default-evaluated-at-import",
                "selection-duplicate-key",
                "field-hook-prefix",
                "field-positional-argument",
                "field-attribute-order",
                "dead-field-attribute",
                "stored-related",
            }
        ),
    ),
)

CROSS_UNIT_RULES = frozenset(
    {
        "unique-over-translated-column",
        "null-exempt-composite-unique",
        "unreadable-source",
    }
)

EMITTED = frozenset(rule for checker in CHECKERS for rule in checker.rules)
