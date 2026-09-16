import unittest


class TestColumnIndexExistsReturnBool(unittest.TestCase):
    class _Cursor:
        def __init__(self, rowcount: int) -> None:
            self.rowcount = rowcount

        def execute(self, *args, **kwargs) -> None:
            pass

    def test_true_is_bool(self):
        from odoo.db.schema import column_exists, index_exists

        cr = self._Cursor(1)
        self.assertIs(column_exists(cr, "t", "c"), True)
        self.assertIs(index_exists(cr, "i"), True)

    def test_false_is_bool(self):
        from odoo.db.schema import column_exists, index_exists

        cr = self._Cursor(0)
        self.assertIs(column_exists(cr, "t", "c"), False)
        self.assertIs(index_exists(cr, "i"), False)


class TestExistenceAdmitsEveryTableKind(unittest.TestCase):
    def test_the_relkinds_are_derived_from_table_kind(self):
        from odoo.db.schema import _EXISTING_RELKINDS, TableKind

        self.assertEqual(set(_EXISTING_RELKINDS), {"r", "v", "m", "f", "p"})
        for kind in TableKind:
            if kind in (TableKind.Temporary, TableKind.Other):
                continue
            self.assertIn(
                kind.value,
                _EXISTING_RELKINDS,
                "a kind get_table_kind can name but get_tables_existing "
                "reports as absent makes _auto_init issue CREATE TABLE over "
                "it and the registry fail to load with DuplicateTable",
            )

    def test_the_query_asks_for_exactly_those(self):
        from odoo.db.schema import _EXISTING_RELKINDS, get_tables_existing

        class _Cursor:
            params = None

            def execute(self, query):
                self.params = query.params

            def fetchall(self):
                return []

        cr = _Cursor()
        get_tables_existing(cr, ["t"])  # type: ignore[arg-type]
        self.assertEqual(cr.params, (["t"], list(_EXISTING_RELKINDS)))
