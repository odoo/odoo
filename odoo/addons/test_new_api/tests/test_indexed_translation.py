import odoo.tests
from odoo.addons.base.tests.test_expression import TransactionExpressionCase
from odoo.addons.base.tests.test_translate import SPECIAL_CHARACTERS


@odoo.tests.tagged('post_install', '-at_install')
class TestIndexedTranslation(TransactionExpressionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('fr_FR')

    def test_search_ilike(self):
        record_en = self.env['test_new_api.indexed_translation'].with_context(lang='en_US').create({})
        record_fr = record_en.with_context(lang='fr_FR')
        record_en.name = '<div class="my_class">hello</div>\n<div/>'
        record_fr.name = '<div class="my_class">%bonjour\\</div>\a<div/>'

        self.assertEqual(record_en.name, '<div class="my_class">hello</div>\n<div/>')
        self.assertEqual(record_fr.name, '<div class="my_class">%bonjour\\</div>\a<div/>')

        # matching double quotes
        self.assertEqual(self._search(record_en, [('name', 'ilike', 'class="my_class')]), record_en)

        # escaped and unescaped PG wildcards
        self.assertEqual(self._search(record_en, [('name', 'ilike', r'class%class')]), record_en)
        self.assertEqual(self._search(record_en, [('name', 'ilike', r'class="m_\_class')]), record_en)
        self.assertEqual(self._search(record_en, [('name', 'ilike', 'bonjour')]), record_en.browse())
        self.assertEqual(self._search(record_en, [('name', 'ilike', '</div>\n<div/>')]), record_en)
        self.assertEqual(self._search(record_fr, [('name', 'ilike', '</div>\a<div/>')]), record_fr)
        self.assertEqual(self._search(record_fr, [('name', 'ilike', r'\%bonjour\\')]), record_fr)

        self.assertEqual(
            self._search(record_en, [('name', '=', '<div class="my_class">hello</div>\n<div/>')]),
            record_en,
        )
        self.assertEqual(
            self._search(record_fr, [('name', '=', '<div class="my_class">%bonjour\\</div>\a<div/>')]),
            record_fr,
        )

        # check what the queries look like
        with self.assertQueries(["""
            SELECT "test_new_api_indexed_translation"."id"
            FROM "test_new_api_indexed_translation"
            WHERE (jsonb_path_query_array("test_new_api_indexed_translation"."name", '$.*')::text ILIKE %s
            AND ("test_new_api_indexed_translation"."name"->>%s ILIKE %s))
            ORDER BY "test_new_api_indexed_translation"."id"
        """, """
            SELECT "test_new_api_indexed_translation"."id"
            FROM "test_new_api_indexed_translation"
            WHERE (jsonb_path_query_array("test_new_api_indexed_translation"."name", '$.*')::text ILIKE %s
            AND (COALESCE("test_new_api_indexed_translation"."name"->>%s, "test_new_api_indexed_translation"."name"->>%s) ILIKE %s))
            ORDER BY "test_new_api_indexed_translation"."id"
        """, """
            SELECT "test_new_api_indexed_translation"."id"
            FROM "test_new_api_indexed_translation"
            WHERE TRUE
            ORDER BY "test_new_api_indexed_translation"."id"
        """, """
            SELECT "test_new_api_indexed_translation"."id"
            FROM "test_new_api_indexed_translation"
            WHERE FALSE
            ORDER BY "test_new_api_indexed_translation"."id"
        """]):
            record_en.search([('name', 'ilike', 'foo')])
            record_fr.search([('name', 'ilike', 'foo')])
            record_fr.search([('name', 'ilike', '')])
            record_fr.search([('name', 'not ilike', '')])

    def test_search_special_characters(self):
        name_en = f'{SPECIAL_CHARACTERS}_en'
        name_fr = f'{SPECIAL_CHARACTERS}_fr'
        record_en = self.env['test_new_api.indexed_translation'].with_context(lang='en_US').create({})
        record_fr = record_en.with_context(lang='fr_FR')
        record_en.name = name_en
        record_fr.name = name_fr

        self.assertEqual(self._search(record_en, [('name', 'ilike', name_en)]), record_en)
        self.assertEqual(self._search(record_en, [('name', '=', name_en)]), record_en)
        self.assertEqual(self._search(record_en, [('name', 'in', [name_en])]), record_en)

        self.assertEqual(self._search(record_fr, [('name', 'ilike', name_fr)]), record_en)
        self.assertEqual(self._search(record_fr, [('name', '=', name_fr)]), record_en)
        self.assertEqual(self._search(record_fr, [('name', 'in', [name_fr])]), record_en)

        self.assertFalse(self._search(record_fr, [('name', 'ilike', name_en)]))
        self.assertFalse(self._search(record_fr, [('name', '=', name_en)]))
        self.assertFalse(self._search(record_fr, [('name', 'in', [name_en])]))

        self.assertFalse(self._search(record_en, [('name', 'ilike', name_fr)]))
        self.assertFalse(self._search(record_en, [('name', '=', name_fr)]))
        self.assertFalse(self._search(record_en, [('name', 'in', [name_fr])]))
