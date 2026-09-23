import ast
import tempfile
from collections import defaultdict
from pathlib import Path

from . import _access_index as index
from . import lint_case
from odoo.addons.base.models.ir_access import domain_group_tests, find_access_cycle

# the methods through which a model decides access in code instead of in rows
_CHECK_OVERRIDES = frozenset({"_check_access", "_has_field_access", "_access_domain"})
# what marks a _search override as one that filters for access
_SEARCH_ACCESS_NAMES = frozenset(
    {
        "bypass_access",
        "_check_access",
        "_filtered_access",
        "has_access",
        "check_access",
        "get_accessible_query",
        "get_inaccessible_owners",
    }
)


def _production(row_or_module) -> bool:
    module = getattr(row_or_module, "module", row_or_module)
    return not module.startswith("test_")


def kind_findings(rows):
    # a guard on a group binds everyone unless it says it binds the members
    return [
        f"{row.where()}: no kind"
        for row in rows
        if row.creates and row.kind not in ("permission", "guard")
    ] + [
        f"{row.where()}: a guard of {row.group} that does not say whom it binds"
        for row in rows
        if row.creates
        and row.kind == "guard"
        and not row.guard_scope
        and (row.group or "").split(".")[-1] != "group_everyone"
    ]


def operation_findings(rows):
    return [
        f"{row.where()}: no operation"
        for row in rows
        if row.creates and not row.operation
    ]


def domain_findings(rows):
    return [
        f"{row.where()}: {problem}"
        for row in rows
        if row.domain and index.known_model(row.model)
        for problem in index.validate(row.model, row.domain)
    ]


def group_test_findings(rows):
    return [
        f"{row.where()}: reads {', '.join(tests)}"
        for row in rows
        if row.domain and (tests := domain_group_tests(row.domain))
    ]


def coverage_findings(rows, models):
    covered = {row.model for row in rows if row.kind == "permission"}
    return sorted(
        f"{info.defined_in}: {name}"
        for name, info in models.items()
        if info.kind == "model" and name not in covered and _production(info.module)
    )


def cycle_findings(rows, models):
    edges: defaultdict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    for name, info in models.items():
        if info.kind == "abstract" or not info.inherits_rules:
            continue
        for parent in info.inherits:
            for operation in index.OPERATIONS.values():
                edges[name, operation].add((parent, operation))
    for row in rows:
        targets = index.access_edges(row)
        for letter, operation in index.OPERATIONS.items():
            if letter in (row.operation or ""):
                edges[row.model, operation].update(targets)
    findings = []
    while cycle := find_access_cycle(edges):
        findings.append(" -> ".join(f"{model}.{op}" for model, op in cycle))
        model, operation = cycle[0]
        edges[model, operation].discard(cycle[1])
    return findings


def override_findings(paths):
    findings = []
    for path in paths:
        try:
            tree = ast.parse(Path(path).read_text(encoding="utf-8"))
        except SyntaxError, UnicodeDecodeError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for method in node.body:
                if not isinstance(method, ast.FunctionDef):
                    continue
                if method.name in _CHECK_OVERRIDES or (
                    method.name == "_search"
                    and _SEARCH_ACCESS_NAMES
                    & {
                        getattr(child, "id", None) or getattr(child, "attr", None)
                        for child in ast.walk(method)
                    }
                ):
                    findings.append(f"{path}:{method.lineno} {node.name}.{method.name}")
    return findings


def old_format_findings(paths):
    findings = []
    for path in paths:
        name = Path(path).name
        if name.startswith("ir.model.access") and name.endswith(".csv"):
            findings.append(f"{path}: an ir.model.access CSV")
        elif name.endswith(".xml"):
            try:
                text = Path(path).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            findings.extend(
                f"{path}: a {model} record"
                for model in ("ir.rule", "ir.model.access")
                if f'model="{model}"' in text or f"model='{model}'" in text
            )
    return findings


def override_paths():
    return [
        path
        for path in lint_case.module_file_paths()
        if path.endswith(".py")
        and lint_case.is_core_path(path)
        and "/odoo/addons/base/" not in path
        and not any(
            part == "tests" or part.startswith("test_") for part in path.split("/")
        )
        and "/migrations/" not in path
    ]


class TestAccessRows(lint_case.LintCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rows = index.rows()
        cls.production_rows = [row for row in cls.rows if _production(row)]

    def test_the_scan_reaches_the_rows_and_the_models(self):
        self.assertGreater(len(self.rows), 3000, "the scan reached almost no row")
        self.assertGreater(len(index.models()), 1000)
        self.assertTrue(
            any(row.path.endswith(".xml") for row in self.rows),
            "the scan reached no ir_access.xml",
        )

    def test_every_row_declares_its_kind(self):
        self.assert_ratchet(
            kind_findings(self.rows),
            "access_kind_explicit",
            "ir.access row(s) created without a kind",
            "A row is a permission (adds records, OR-ed) or a guard (AND-ed, cannot "
            "be widened): say which in the `kind` column or field.",
        )

    def test_every_row_writes_its_operation(self):
        self.assert_ratchet(
            operation_findings(self.rows),
            "access_rule_mode",
            "ir.access row(s) created without an operation",
            "A row that names no operation would apply to all four: write the "
            "`operation` (a subset of crud) it is meant for.",
        )

    def test_every_shipped_domain_validates(self):
        self.assert_ratchet(
            domain_findings(self.rows),
            "access_domain_validated",
            "ir.access domain(s) naming what the models do not have",
            "A path, an operator or an 'access' condition the registry cannot "
            "answer fails at load or, worse, decides nothing: fix the domain.",
        )

    def test_no_domain_tests_the_user_s_groups(self):
        self.assert_ratchet(
            group_test_findings(self.rows),
            "access_domain_no_group_test",
            "ir.access domain(s) reading the user's groups in a narrowing way",
            "Membership is the row's group: a domain that reads the user's groups "
            "(other than `in user.all_group_ids.ids` or `[] if has_group else D`) "
            "lets a group take records away. Put the rows on the groups.",
        )

    def test_every_model_holds_a_permission(self):
        self.assert_ratchet(
            coverage_findings(self.production_rows, index.models()),
            "access_model_covered",
            "model(s) no permission row names",
            "A model without a permission is readable by the superuser only: ship "
            "the permission rows in the module's security/ir.access.csv.",
        )

    def test_the_access_graph_has_no_cycle(self):
        self.assert_ratchet(
            cycle_findings(self.rows, index.models()),
            "access_delegation_acyclic",
            "cycle(s) through 'access' conditions and delegation",
            "A record's access cannot depend on itself: break the cycle with a "
            "domain that does not go through the 'access' operator.",
        )

    def test_access_is_decided_in_rows_not_in_code(self):
        self.assert_ratchet(
            override_findings(override_paths()),
            "access_check_override",
            "override(s) deciding access in code outside base",
            "State what a model requires in ir.access rows or in `_access_guard` "
            "(an 'access' condition on the record it belongs to); a scan in code "
            "is what P4 retires.",
        )

    def test_no_module_ships_the_retired_access_format(self):
        self.assert_ratchet(
            old_format_findings(
                path
                for path in lint_case.module_file_paths()
                if lint_case.is_core_path(path)
                and "/migrations/" not in path
                and "/upgrades/" not in path
                and "/static/" not in path
            ),
            "access_retired_format",
            "file(s) shipping ir.model.access lines or ir.rule records",
            "Those models are gone and the loader refuses their data: ship "
            "security/ir.access.csv (id,name,model_id/id,group_id/id,kind,"
            "operation,domain); base's ir_access_convert converts the old rows.",
        )


class TestAccessRowGatesSeeTheirFaults(lint_case.LintCase):
    # each gate reads a planted fault, so a gate that goes blind reads red here

    def _row(self, **values):
        defaults = {
            "module": "planted",
            "xmlid": "planted.row",
            "path": "planted.csv",
            "line": 2,
            "model": "res.partner",
            "group": "base.group_user",
            "kind": "permission",
            "operation": "r",
            "domain": None,
            "creates": True,
        }
        return index.Row(**(defaults | values))

    def test_a_row_without_kind_or_operation(self):
        self.assertEqual(len(kind_findings([self._row(kind=None)])), 1)
        self.assertEqual(len(operation_findings([self._row(operation=None)])), 1)
        self.assertFalse(kind_findings([self._row(kind=None, creates=False)]))
        member_guard = self._row(kind="guard", group="x.group_restricted")
        self.assertEqual(len(kind_findings([member_guard])), 1)
        member_guard.guard_scope = "members"
        self.assertFalse(kind_findings([member_guard]))
        self.assertFalse(
            kind_findings([self._row(kind="guard", group="base.group_everyone")])
        )

    def test_a_domain_the_registry_cannot_answer(self):
        for domain in (
            "[('no_such_field', '=', 1)]",
            "[('company_id.no_such_field', '=', 1)]",
            "[('name', 'no such operator', 1)]",
            "[('name', 'access', 'read')]",
            "[('parent_id', 'any', [('no_such_field', '=', 1)])]",
            "[('parent_id'",
        ):
            with self.subTest(domain=domain):
                self.assertTrue(domain_findings([self._row(domain=domain)]))
        self.assertFalse(
            domain_findings(
                [
                    self._row(
                        domain="[('parent_id', 'access', 'read'), ('name', '!=', 1)]"
                    )
                ]
            )
        )

    def test_a_domain_testing_the_user_s_groups(self):
        self.assertTrue(
            group_test_findings(
                [self._row(domain="[('id', '=', 1)] if user.has_group('x.y') else []")]
            )
        )
        self.assertFalse(
            group_test_findings(
                [self._row(domain="[] if user.has_group('x.y') else [('id', '=', 1)]")]
            )
        )

    def test_a_model_without_a_permission(self):
        models = {"planted.model": index.ModelInfo("planted.model", module="planted")}
        self.assertTrue(coverage_findings([], models))
        self.assertFalse(coverage_findings([self._row(model="planted.model")], models))

    def test_a_cycle_through_the_operator(self):
        models = {
            "res.partner": index.ModelInfo("res.partner"),
            "res.users": index.ModelInfo("res.users"),
        }
        forth = self._row(
            model="res.users", domain="[('partner_id', 'access', 'read')]"
        )
        back = self._row(model="res.partner", domain="[('user_id', 'access', 'read')]")
        self.assertTrue(cycle_findings([forth, back], models))
        self.assertFalse(cycle_findings([forth], models))

    def test_a_module_shipping_the_retired_format(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / "ir.model.access.csv").write_text("id,name\n")
        (root / "rules.xml").write_text('<odoo><record model="ir.rule"/></odoo>')
        (root / "views.xml").write_text('<odoo><record model="ir.ui.view"/></odoo>')
        self.assertEqual(
            len(old_format_findings(str(path) for path in root.iterdir())), 2
        )

    def test_an_override_deciding_access_in_code(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "m.py"
        path.write_text(
            "class M(models.Model):\n"
            "    def _check_access(self, operation):\n"
            "        return None\n"
            "    def _search(self, domain, *, bypass_access=False, **kw):\n"
            "        return super()._search(domain, bypass_access=bypass_access)\n"
            "    def _read(self):\n"
            "        return None\n"
        )
        self.assertEqual(len(override_findings([str(path)])), 2)
