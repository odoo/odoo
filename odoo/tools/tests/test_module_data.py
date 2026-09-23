import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from odoo.modules.registry import Registry
from odoo.tools.module_data import (
    CRON_ACTION_SUFFIX,
    READONLY_MERGED_MODULE,
    _table_of,
    absorb_readonly_forerunners,
    adopt_xmlids,
    rehome_cron_xmlids,
    repair_orphaned_cron_actions,
)

BaseCase = unittest.TestCase


class _Cursor:
    def __init__(self, xmlids, installed=(), records=None):
        self.xmlids = dict(xmlids)
        self.records = records or {rid: ("res.partner", rid) for rid in self.xmlids}
        self.modules = dict.fromkeys(installed, "installed")
        self.statements = []
        self._result = []
        self.rowcount = 0

    def execute(self, query, params=None):
        code = " ".join(str(query.code).split())
        params = list(query.params) if params is None else list(params)
        self.statements.append((code, params))
        self._result = []
        self.rowcount = 0
        if code.startswith("SELECT id, name FROM ir_model_data WHERE module = %s"):
            self._result = [
                (rid, name)
                for rid, (mod, name) in self.xmlids.items()
                if mod == params[0]
            ]
        elif code.startswith(
            "UPDATE ir_model_data SET module = %s, name = %s WHERE id = %s"
        ):
            to_module, new_name, rid = params
            if rid in self.xmlids:
                self.xmlids[rid] = (to_module, new_name)
                self.rowcount = 1
        elif code.startswith("SELECT source.id, source.name, target.name"):
            olds, news, from_module, to_module = params
            for old, new in zip(olds, news, strict=True):
                source = self._find(from_module, old)
                target = self._find(to_module, new)
                if source is not None and target is not None and source != target:
                    same = self.records.get(source) == self.records.get(target)
                    self._result.append((source, old, new, same))
        elif code.startswith("DELETE FROM ir_model_data WHERE id = ANY(%s)"):
            for rid in params[0]:
                self.rowcount += self.xmlids.pop(rid, None) is not None
        elif code.startswith(
            "UPDATE ir_model_data data SET module = %s, name = pair.new"
        ):
            to_module, olds, news, from_module = params
            for old, new in zip(olds, news, strict=True):
                if (rid := self._find(from_module, old)) is not None:
                    self.xmlids[rid] = (to_module, new)
                    self.rowcount += 1
        elif code.startswith("SELECT 1 FROM ir_model_data WHERE module = %s"):
            self._result = (
                [(1,)] if any(m == params[0] for m, _ in self.xmlids.values()) else []
            )
        elif code.startswith("UPDATE ir_module_module SET state = 'uninstalled'"):
            if self.modules.get(params[0], "uninstalled") != "uninstalled":
                self.modules[params[0]] = "uninstalled"
                self.rowcount = 1
        elif code.startswith(
            (
                "UPDATE ir_module_module SET auto_install = FALSE",
                "DELETE FROM ir_module_module_dependency",
            )
        ):
            pass
        else:
            raise AssertionError(f"unexpected statement: {code}")

    def _find(self, module, name):
        return next(
            (rid for rid, key in self.xmlids.items() if key == (module, name)), None
        )

    def fetchall(self):
        return list(self._result)

    def fetchone(self):
        return self._result[0] if self._result else None


FORERUNNER_ROWS = {
    1: ("sale_group_readonly", "group_sale_readonly"),
    2: ("sale_group_readonly", "access_crm_tag_readonly"),
    3: ("sale_group_readonly", "access_account_move_readonly"),
    4: ("stock_group_readonly", "group_stock_readonly"),
    5: ("stock_group_readonly", "access_stock_picking_readonly"),
    6: ("purchase_group_readonly", "access_stock_picking_readonly"),
    7: ("mail", "group_mail_something"),
}


class TestAbsorbReadonlyForerunners(BaseCase):
    def test_rows_move_under_the_merged_module_with_domain_suffixed_acl_names(self):
        cr = _Cursor(
            FORERUNNER_ROWS, installed=("sale_group_readonly", "stock_group_readonly")
        )
        moved = absorb_readonly_forerunners(cr)
        self.assertEqual(moved, 6)
        merged = {
            name for mod, name in cr.xmlids.values() if mod == READONLY_MERGED_MODULE
        }
        self.assertEqual(
            merged,
            {
                "group_sale_readonly",
                "access_crm_tag_sale_readonly",
                "access_account_move_sale_readonly",
                "group_stock_readonly",
                "access_stock_picking_stock_readonly",
                "access_stock_picking_purchase_readonly",
            },
        )
        self.assertEqual(cr.xmlids[1], (READONLY_MERGED_MODULE, "group_sale_readonly"))
        self.assertEqual(cr.xmlids[7], ("mail", "group_mail_something"))

    def test_the_forerunner_modules_are_retired_once_emptied(self):
        cr = _Cursor(
            FORERUNNER_ROWS, installed=("sale_group_readonly", "stock_group_readonly")
        )
        absorb_readonly_forerunners(cr)
        self.assertEqual(cr.modules["sale_group_readonly"], "uninstalled")
        self.assertEqual(cr.modules["stock_group_readonly"], "uninstalled")

    def test_a_database_that_took_the_intermediate_step_is_a_no_op(self):
        already = {
            1: (READONLY_MERGED_MODULE, "group_sale_readonly"),
            2: ("sale_team", "group_sale_readonly"),
        }
        cr = _Cursor(already)
        self.assertEqual(absorb_readonly_forerunners(cr), 0)
        self.assertEqual(cr.xmlids, already)
        self.assertEqual(cr.modules, {})

    def test_the_split_adoption_then_finds_the_absorbed_rows(self):
        cr = _Cursor(FORERUNNER_ROWS, installed=("sale_group_readonly",))
        self.assertEqual(
            adopt_xmlids(
                cr, READONLY_MERGED_MODULE, "sale_team", ("group_sale_readonly",)
            ),
            0,
        )
        absorb_readonly_forerunners(cr)
        self.assertEqual(
            adopt_xmlids(
                cr,
                READONLY_MERGED_MODULE,
                "sale_team",
                ("group_sale_readonly", "access_crm_tag_sale_readonly"),
            ),
            2,
        )
        self.assertEqual(cr.xmlids[1], ("sale_team", "group_sale_readonly"))
        self.assertEqual(cr.xmlids[2], ("sale_team", "access_crm_tag_sale_readonly"))


CRON = "ir_cron_find_and_set_documents_expired"
RENAMED_CRON = "ir_cron_document_expiration_refresh"


class TestRehomeCronXmlids(BaseCase):
    def test_the_server_action_companion_moves_with_its_cron(self):
        cr = _Cursor(
            {
                1: ("document_compliance", CRON),
                2: ("document_compliance", CRON + CRON_ACTION_SUFFIX),
                3: ("document_compliance", "view_document_type_form"),
            }
        )
        moved = rehome_cron_xmlids(
            cr, "document_compliance", "document", {CRON: RENAMED_CRON}
        )
        self.assertEqual(moved, 2)
        self.assertEqual(cr.xmlids[1], ("document", RENAMED_CRON))
        self.assertEqual(cr.xmlids[2], ("document", RENAMED_CRON + CRON_ACTION_SUFFIX))

    def test_an_unrelated_xmlid_of_the_same_module_is_left_alone(self):
        cr = _Cursor(
            {
                1: ("document_compliance", CRON),
                2: ("document_compliance", CRON + CRON_ACTION_SUFFIX),
                3: ("document_compliance", "view_document_type_form"),
            }
        )
        rehome_cron_xmlids(cr, "document_compliance", "document", {CRON: RENAMED_CRON})
        self.assertEqual(
            cr.xmlids[3], ("document_compliance", "view_document_type_form")
        )

    def test_a_database_already_rehomed_moves_nothing(self):
        already = {
            1: ("document", RENAMED_CRON),
            2: ("document", RENAMED_CRON + CRON_ACTION_SUFFIX),
        }
        cr = _Cursor(already)
        self.assertEqual(
            rehome_cron_xmlids(
                cr, "document_compliance", "document", {CRON: RENAMED_CRON}
            ),
            0,
        )
        self.assertEqual(cr.xmlids, already)


class _RepairCursor:
    """Answers the two statements ``repair_orphaned_cron_actions`` issues.

    ``orphans`` are the rows the scan returns; ``taken`` are the (module, name)
    pairs already spoken for, which is what the UPDATE's NOT EXISTS guards on.
    """

    def __init__(self, orphans, taken=()):
        self.orphans = list(orphans)
        self.taken = set(taken)
        self.renamed = []
        self.rowcount = 0
        self._result = []

    def execute(self, query, params=None):
        code = " ".join(str(query.code).split())
        params = list(query.params) if params is None else list(params)
        if code.startswith("SELECT stale.id, stale.module, stale.name"):
            self._result = list(self.orphans)
            self.rowcount = len(self.orphans)
        elif code.startswith("UPDATE ir_model_data SET module = %s, name = %s"):
            module, name, data_id = params[0], params[1], params[2]
            self.rowcount = 0 if (module, name) in self.taken else 1
            if self.rowcount:
                self.renamed.append((data_id, module, name))
                self.taken.add((module, name))
        else:
            raise AssertionError(f"unexpected statement: {code}")

    def fetchall(self):
        return list(self._result)

    def fetchone(self):
        raise AssertionError("repair_orphaned_cron_actions reads rows, never one row")


class TestRepairOrphanedCronActions(BaseCase):
    ORPHAN = (
        10017696,
        "document_compliance",
        CRON + CRON_ACTION_SUFFIX,
        "document",
        RENAMED_CRON,
    )

    def test_the_companion_is_repointed_at_the_cron_it_drives(self):
        cr = _RepairCursor([self.ORPHAN])
        self.assertEqual(repair_orphaned_cron_actions(cr), 1)
        self.assertEqual(
            cr.renamed,
            [(10017696, "document", RENAMED_CRON + CRON_ACTION_SUFFIX)],
        )

    def test_a_database_with_nothing_to_repair_is_a_no_op(self):
        cr = _RepairCursor([])
        self.assertEqual(repair_orphaned_cron_actions(cr), 0)
        self.assertEqual(cr.renamed, [])

    def test_a_name_another_row_already_holds_is_not_taken_from_it(self):
        cr = _RepairCursor(
            [self.ORPHAN],
            taken={("document", RENAMED_CRON + CRON_ACTION_SUFFIX)},
        )
        self.assertEqual(repair_orphaned_cron_actions(cr), 0)
        self.assertEqual(cr.renamed, [])


class TestAdoptXmlidsOntoATakenName(BaseCase):
    def test_a_name_already_on_the_same_record_drops_the_duplicate(self):
        cr = _Cursor(
            {1: ("old_mod", "rec"), 2: ("new_mod", "rec")},
            records={1: ("res.partner", 7), 2: ("res.partner", 7)},
        )
        self.assertEqual(adopt_xmlids(cr, "old_mod", "new_mod", ("rec",)), 1)
        self.assertEqual(cr.xmlids, {2: ("new_mod", "rec")})

    def test_a_name_on_another_record_stops_the_upgrade_by_name(self):
        cr = _Cursor(
            {1: ("old_mod", "rec"), 2: ("new_mod", "rec")},
            records={1: ("res.partner", 7), 2: ("res.partner", 8)},
        )
        with self.assertRaisesRegex(ValueError, r"\['rec -> rec'\]"):
            adopt_xmlids(cr, "old_mod", "new_mod", ("rec",))
        self.assertEqual(cr.xmlids, {1: ("old_mod", "rec"), 2: ("new_mod", "rec")})

    def test_every_name_moves_in_one_statement(self):
        cr = _Cursor({rid: ("old_mod", f"rec_{rid}") for rid in range(1, 6)})
        adopt_xmlids(cr, "old_mod", "new_mod", [f"rec_{rid}" for rid in range(1, 6)])
        self.assertEqual(
            [code for code, _params in cr.statements if code.startswith("UPDATE")],
            [
                (
                    "UPDATE ir_model_data data SET module = %s, name = pair.new "
                    "FROM unnest(%s::varchar[], %s::varchar[]) AS pair(old, new) "
                    "WHERE data.module = %s AND data.name = pair.old"
                )
            ],
        )
        self.assertEqual({mod for mod, _name in cr.xmlids.values()}, {"new_mod"})


def _workspace(checkout: Path) -> Path:
    # a worktree's `.git` is a file naming <checkout>/.git/worktrees/<name>
    git = checkout / ".git"
    if git.is_file():
        return Path(git.read_text().split(":", 1)[1].strip()).parents[2].parent
    return checkout.parent


def _declared_tables():
    checkout = Path(__file__).resolve().parents[3]
    workspace = _workspace(checkout)
    trees = [checkout / "odoo" / "addons", checkout / "addons"] + [
        workspace / repo for repo in ("enterprise", "agromarin", "design-themes")
    ]
    for tree in trees:
        for path in tree.rglob("*.py") if tree.is_dir() else ():
            source = path.read_text(errors="replace")
            if "_table" not in source:
                continue
            for node in ast.walk(ast.parse(source)):
                if not isinstance(node, ast.ClassDef):
                    continue
                assigned = {
                    target.id: statement.value.value
                    for statement in node.body
                    if isinstance(statement, ast.Assign)
                    and isinstance(statement.value, ast.Constant)
                    and isinstance(statement.value.value, str)
                    for target in statement.targets
                    if isinstance(target, ast.Name)
                }
                if "_table" in assigned and "_name" in assigned:
                    yield path, assigned["_name"], assigned["_table"]


class TestTableOfAModel(BaseCase):
    def test_every_table_a_model_declares_is_known_before_a_registry(self):
        declared = list(_declared_tables())
        self.assertIn("ir.actions.server", {name for _path, name, _t in declared})
        wrong = {
            name: (table, _table_of(name))
            for _path, name, table in declared
            if _table_of(name) != table
        }
        self.assertEqual(wrong, {})

    def test_a_loaded_registry_answers_first(self):
        registry = {"probe.model": SimpleNamespace(_table="probe_elsewhere")}
        with mock.patch.object(Registry, "registries", {"probe_db": registry}):
            cr = SimpleNamespace(dbname="probe_db")
            self.assertEqual(_table_of("probe.model", cr), "probe_elsewhere")
            self.assertEqual(_table_of("probe.other", cr), "probe_other")
            self.assertEqual(_table_of("ir.actions.server", cr), "ir_act_server")
