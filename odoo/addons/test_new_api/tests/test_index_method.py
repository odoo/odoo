from odoo.tests import TransactionCase, tagged
from odoo.tools import sql


@tagged('post_install', '-at_install')
class TestIndexMethodMigration(TransactionCase):
    """``Registry.check_indexes`` must rebuild a column index when the field
    changes the kind of index it wants (e.g. btree -> trigram), even though
    the index name stays the same."""

    def _index_method(self, indexname):
        self.cr.execute(
            """
            SELECT am.amname
              FROM pg_class idx
              JOIN pg_am am ON am.oid = idx.relam
             WHERE idx.relname = %s
            """,
            [indexname],
        )
        row = self.cr.fetchone()
        return row[0] if row else None

    def test_index_rebuilt_when_method_changes(self):
        registry = self.registry
        if not registry.has_trigram:
            self.skipTest("pg_trgm extension is required for trigram indexes")

        cr = self.cr
        field = registry['res.partner']._fields['ref']
        indexname = sql.make_index_name('res_partner', 'ref')

        # Reproduce the state an upgraded database carries: the column is
        # indexed with a btree, named after the convention, while the field
        # definition now asks for a trigram index.
        sql.drop_index(cr, indexname, 'res_partner')
        sql.create_index(cr, indexname, 'res_partner', ['"ref"'], 'btree')
        self.assertEqual(self._index_method(indexname), 'btree')

        original_index = field.index
        field.index = 'trigram'
        self.addCleanup(setattr, field, 'index', original_index)

        registry.check_indexes(cr, ['res.partner'])

        # The obsolete btree index must have been dropped and rebuilt as a
        # gin/trigram index under the same name.
        self.assertEqual(self._index_method(indexname), 'gin')
