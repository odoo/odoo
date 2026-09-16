import unittest

from odoo.tools.module_data import (
    CRON_ACTION_SUFFIX,
    READONLY_MERGED_MODULE,
    absorb_readonly_forerunners,
    adopt_xmlids,
    rehome_cron_xmlids,
    repair_orphaned_cron_actions,
)

BaseCase = unittest.TestCase


class _Cursor:
    def __init__(self, xmlids, installed=()):
        self.xmlids = dict(xmlids)
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
        elif code.startswith(
            "UPDATE ir_model_data SET module = %s, name = %s WHERE module = %s AND name = %s"
        ):
            to_module, new_name, from_module, old_name = params
            for rid, (mod, name) in self.xmlids.items():
                if (mod, name) == (from_module, old_name):
                    self.xmlids[rid] = (to_module, new_name)
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
