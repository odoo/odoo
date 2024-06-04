# -*- coding: utf-8 -*-

import threading
from concurrent.futures import ThreadPoolExecutor

from psycopg2 import IntegrityError

import odoo.tests
from odoo.addons.base.tests.test_translate import SPECIAL_CHARACTERS
from odoo.modules.registry import Registry, DummyRLock
from odoo.tools import mute_logger
from odoo.exceptions import ValidationError


@odoo.tests.tagged('post_install', '-at_install')
class TestIndexedTranslation(odoo.tests.TransactionCase):

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
        self.assertEqual(record_en.search([('name', 'ilike', 'class="my_class')]), record_en)

        # escaped and unescaped PG wildcards
        self.assertEqual(record_en.search([('name', 'ilike', 'class%class')]), record_en)
        self.assertEqual(record_en.search([('name', 'ilike', r'class="m_\_class')]), record_en)
        self.assertEqual(record_en.search([('name', 'ilike', 'bonjour')]), record_en.browse())
        self.assertEqual(record_en.search([('name', 'ilike', '</div>\n<div/>')]), record_en)
        self.assertEqual(record_fr.search([('name', 'ilike', '</div>\a<div/>')]), record_fr)
        self.assertEqual(record_fr.search([('name', 'ilike', r'\%bonjour\\')]), record_fr)

        self.assertEqual(
            record_en.search([('name', '=', '<div class="my_class">hello</div>\n<div/>')]),
            record_en,
        )
        self.assertEqual(
            record_fr.search([('name', '=', '<div class="my_class">%bonjour\\</div>\a<div/>')]),
            record_fr,
        )

        # check what the queries look like
        with self.assertQueries(["""
            SELECT "test_new_api_indexed_translation"."id"
            FROM "test_new_api_indexed_translation"
            WHERE (jsonb_path_query_array("test_new_api_indexed_translation"."name", '$.*')::text ILIKE %s
            AND "test_new_api_indexed_translation"."name"->>%s ILIKE %s)
            ORDER BY "test_new_api_indexed_translation"."id"
        """, """
            SELECT "test_new_api_indexed_translation"."id"
            FROM "test_new_api_indexed_translation"
            WHERE (jsonb_path_query_array("test_new_api_indexed_translation"."name", '$.*')::text ILIKE %s
            AND COALESCE("test_new_api_indexed_translation"."name"->>%s, "test_new_api_indexed_translation"."name"->>%s) ILIKE %s)
            ORDER BY "test_new_api_indexed_translation"."id"
        """, """
            SELECT "test_new_api_indexed_translation"."id"
            FROM "test_new_api_indexed_translation"
            WHERE TRUE
            ORDER BY "test_new_api_indexed_translation"."id"
        """, """
            SELECT "test_new_api_indexed_translation"."id"
            FROM "test_new_api_indexed_translation"
            WHERE "test_new_api_indexed_translation"."name" IS NULL
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

        self.assertEqual(record_en.search([('name', 'ilike', name_en)]), record_en)
        self.assertEqual(record_en.search([('name', '=', name_en)]), record_en)
        self.assertEqual(record_en.search([('name', 'in', [name_en])]), record_en)

        self.assertEqual(record_fr.search([('name', 'ilike', name_fr)]), record_en)
        self.assertEqual(record_fr.search([('name', '=', name_fr)]), record_en)
        self.assertEqual(record_fr.search([('name', 'in', [name_fr])]), record_en)

        self.assertFalse(record_fr.search([('name', 'ilike', name_en)]))
        self.assertFalse(record_fr.search([('name', '=', name_en)]))
        self.assertFalse(record_fr.search([('name', 'in', [name_en])]))

        self.assertFalse(record_en.search([('name', 'ilike', name_fr)]))
        self.assertFalse(record_en.search([('name', '=', name_fr)]))
        self.assertFalse(record_en.search([('name', 'in', [name_fr])]))


@odoo.tests.tagged('-standard', '-at_install', 'post_install', 'database_breaking')
class TestUniqueTranslationConcurrently(odoo.tests.TransactionCase):
        def setUp(self):
            super().setUp()
            self.env['res.lang']._activate_lang('en_UK')
            self.env['res.lang']._activate_lang('fr_FR')
            # ormcache the languages for sub-threads to allow languages to be
            # logically activated before the commit of the main thread
            self.env['res.lang']._get_active_by('code')
            self.patch(Registry, "_lock", DummyRLock())  # prevent deadlock (see #161438)

        # @mute_logger('odoo.sql_db')
        def _check_create_tags_concurrently(self, create_vals_1, create_vals_2, lang):
            barrier = threading.Barrier(2)

            with self.registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                self.assertEqual(len(env['test_new_api.unique.translated.tags'].search([])), 0)

            def create_tag(create_vals, context):
                raised_unique_violation = False

                with self.registry.cursor() as cr:
                    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, context)
                    self.assertFalse(env['test_new_api.unique.translated.tags'].search([]))
                    barrier.wait(timeout=2)
                    try:
                        env['test_new_api.unique.translated.tags'].create([create_vals])
                    except IntegrityError as e:
                        if e.pgcode == "23505":  # UniqueViolation
                            raised_unique_violation = True

                return raised_unique_violation

            with ThreadPoolExecutor(max_workers=2) as executor:
                future_1 = executor.submit(create_tag, create_vals_1, {'lang': lang})
                future_2 = executor.submit(create_tag, create_vals_2, {'lang': lang})
                raised_1 = future_1.result(timeout=3)
                raised_2 = future_2.result(timeout=3)

            with self.registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                tags = env['test_new_api.unique.translated.tags'].search([])
                tags_num = len(tags)
                tags.unlink()  # clean up the tags created by the committed sub threads

            raised_num = raised_1 + raised_2
            return tags_num, raised_num

        # 2 transactions create the same tag in en_US at the same time

        def test_unique_name1_1(self):
            tags_num, raised_num = self._check_create_tags_concurrently(
                {'name1': 'tag_en'},
                {'name1': 'tag_en'},
                'en_US'
            )
            self.assertEqual(tags_num, 1)
            self.assertEqual(raised_num, 1)

        def test_unique_name2_1(self):
            # bad behavior
            tags_num, raised_num = self._check_create_tags_concurrently(
                {'name2': 'tag_en'},
                {'name2': 'tag_en'},
                'en_US'
            )
            self.assertEqual(tags_num, 2)  # 1 is better
            self.assertEqual(raised_num, 0)  # 1 is better

        def test_unique_name3_1(self):
            tags_num, raised_num = self._check_create_tags_concurrently(
                {'name3': 'tag_en'},
                {'name3': 'tag_en'},
                'en_US'
            )
            self.assertEqual(tags_num, 1)
            self.assertEqual(raised_num, 1)

        # 2 transactions create the same tag in non-en_US at the same time

        def test_unique_name1_2(self):
            tags_num, raised_num = self._check_create_tags_concurrently(
                {'name1': 'tag_fr'},
                {'name1': 'tag_fr'},
                'fr_FR'
            )
            self.assertEqual(tags_num, 1)
            self.assertEqual(raised_num, 1)

        def test_unique_name2_2(self):
            # bad behavior
            tags_num, raised_num = self._check_create_tags_concurrently(
                {'name2': 'tag_fr'},
                {'name2': 'tag_fr'},
                'fr_FR'
            )
            self.assertEqual(tags_num, 2)  # 1 is better
            self.assertEqual(raised_num, 0)  # 1 is better

        def test_unique_name3_2(self):
            tags_num, raised_num = self._check_create_tags_concurrently(
                {'name3': 'tag_fr'},
                {'name3': 'tag_fr'},
                'fr_FR'
            )
            self.assertEqual(tags_num, 1)
            self.assertEqual(raised_num, 1)


class TestUniqueTranslationSequentially(odoo.tests.TransactionCase):
    def setUp(self):
        super().setUp()
        self.env['res.lang']._activate_lang('en_GB')
        self.env['res.lang']._activate_lang('fr_FR')

    # @mute_logger('odoo.sql_db')
    def _check_create_existing_tag(self, existing_translations, create_vals, lang):
        self.assertFalse(self.env['test_new_api.unique.translated.tags'].search([]))
        # prepare existing tags
        ext = self.env['test_new_api.unique.translated.tags'].create({})
        for field_name, translations in existing_translations:
            ext.update_field_translations(field_name, translations)
        ext.flush_recordset()
        # create new tag
        raised_unique_violation = False
        try:
            self.env['test_new_api.unique.translated.tags'].with_context(lang=lang).create([create_vals])
        except IntegrityError as e:
            if e.pgcode == "23505":  # UniqueViolation
                raised_unique_violation = True
        except ValidationError:
            raised_unique_violation = True
        return raised_unique_violation

    # create a tag with the same name in en_US as an existing tag

    def test_unique_name1_1(self):
        self.assertTrue(self._check_create_existing_tag(
            [('name1', {'en_US': 'tag_en'})],
            {'name1': 'tag_en'},
            'en_US'
        ))

    def test_unique_name2_1(self):
        self.assertTrue(self._check_create_existing_tag(
            [('name3', {'en_US': 'tag_en'})],
            {'name3': 'tag_en'},
            'en_US'
        ))

    def test_unique_name3_1(self):
        self.assertTrue(self._check_create_existing_tag(
            [('name3', {'en_US': 'tag_en'})],
            {'name3': 'tag_en'},
            'en_US'
        ))

    # create a tag with the same name in fr_FR as an existing tag

    def test_unique_name1_2(self):
        # bad behavior
        self.assertFalse(self._check_create_existing_tag(
            [('name1', {'en_US': 'tag_en', 'fr_FR': 'tag_fr'})],
            {'name1': 'tag_fr'},
            'fr_FR'
        ))

    def test_unique_name2_2(self):
        self.assertTrue(self._check_create_existing_tag(
            [('name2', {'en_US': 'tag_en', 'fr_FR': 'tag_fr'})],
            {'name2': 'tag_fr'},
            'fr_FR'
        ))

    def test_unique_name3_2(self):
        self.assertTrue(self._check_create_existing_tag(
            [('name3', {'en_US': 'tag_en', 'fr_FR': 'tag_fr'})],
            {'name3': 'tag_fr'},
            'fr_FR'
        ))

    # create a tag with the same name in en_GB as an existing en_US tag
    # because the ORM uses en_US as fallback for en_GB and sometimes en_GB is
    # not translated, because the translation is the same as en_US.

    def test_unique_name1_3(self):
        # bad behavior
        self.assertFalse(self._check_create_existing_tag(
            [('name1', {'en_US': 'tag_en'})],
            {'name1': 'tag_en'},
            'en_GB'
        ))

    def test_unique_name2_3(self):
        self.assertTrue(self._check_create_existing_tag(
            [('name2', {'en_US': 'tag_en'})],
            {'name2': 'tag_en'},
            'en_GB'
        ))

    def test_unique_name3_3(self):
        self.assertTrue(self._check_create_existing_tag(
            [('name3', {'en_US': 'tag_en'})],
            {'name3': 'tag_en'},
            'en_GB'
        ))
