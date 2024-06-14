# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import psycopg2

from odoo.addons.website.controllers.main import Website
from odoo.addons.website.tools import MockRequest
import odoo.tests
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)

@odoo.tests.tagged('-at_install', 'post_install')
class TestAutoComplete(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].browse(1)
        cls.WebsiteController = Website()

    def _autocomplete(self, term, expected_count, expected_fuzzy_term, search_type="test", options=None):
        """ Calls the autocomplete for a given term and performs general checks """
        with MockRequest(self.env, website=self.website):
            suggestions = self.WebsiteController.autocomplete(
                search_type=search_type, term=term, max_nb_chars=50, options=options or {},
            )
        self.assertEqual(expected_count, suggestions['results_count'], "Wrong number of suggestions")
        self.assertEqual(expected_fuzzy_term, suggestions.get('fuzzy_search', 'Not found'), "Wrong fuzzy match")

    def _autocomplete_page(self, term, expected_count, expected_fuzzy_term):
        self._autocomplete(term, expected_count, expected_fuzzy_term, search_type="pages", options={
            'displayDescription': False, 'displayDetail': False,
            'displayExtraDetail': False, 'displayExtraLink': False,
            'displayImage': False, 'allowFuzzy': True
        })

    def test_01_many_records(self):
        # REF1000~REF3999
        data = [{
            'name': 'REF%s' % count,
            'is_published': True,
        } for count in range(1000, 4000)]
        self.env['test.model'].create(data)
        # NUM1000~NUM1998
        data = [{
            'name': 'NUM%s' % count,
            'is_published': True,
        } for count in range(1000, 1999)]
        self.env['test.model'].create(data)
        # There are more than 1000 "R*" records
        # => Find exact match through the fallback
        self._autocomplete('REF3000', 1, False)
        # => No exact match => Find fuzzy within first 1000 (distance=3: replace D by F, move 3, add 1)
        self._autocomplete('RED3000', 1, 'ref3000' if self.env.registry.has_trigram else 'ref1003')
        # => Find exact match through the fallback
        self._autocomplete('REF300', 10, False)
        # => Find exact match through the fallback
        self._autocomplete('REF1', 1000, False)
        # => No exact match => Nothing close enough (min distance=5)
        self._autocomplete('REFX', 0, "Not found")
        # => Find exact match through the fallback - unfortunate because already in the first 1000 records
        self._autocomplete('REF1230', 1, False)
        # => Find exact match through the fallback
        self._autocomplete('REF2230', 1, False)

        # There are less than 1000 "N*" records
        # => Fuzzy within N* (distance=1: add 1)
        self._autocomplete('NUM000', 1, "num1000")
        # => Exact match (distance=0 shortcut logic)
        self._autocomplete('NUM100', 10, False)
        # => Exact match (distance=0 shortcut logic)
        self._autocomplete('NUM199', 9, False)
        # => Exact match (distance=0 shortcut logic)
        self._autocomplete('NUM1998', 1, False)
        # => Fuzzy within N* (distance=1: replace 1 by 9)
        self._autocomplete('NUM1999', 1, 'num1199')
        # => Fuzzy within N* (distance=1: add 1)
        self._autocomplete('NUM200', 1, 'num1200')

        # There are no "X*" records
        self._autocomplete('XEF1000', 0, "Not found")

    def test_02_pages_search(self):
        if not self.env.registry.has_trigram:
            try:
                self.env.cr.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
                self.env.registry.has_trigram = True
            except psycopg2.Error:
                _logger.warning("pg_trgm extension can't be installed, which is required to run this test")
                return

        with MockRequest(self.env, website=self.env['website'].browse(1)):
            # This should not crash. This ensures that when searching on `name`
            # field of `website.page` model, it works properly when `pg_trgm` is
            # activated.
            # Indeed, `name` is a field of `website.page` record but only at the
            # ORM level, not in SQL, due to how `inherits` works.
            self.env['website'].browse(1)._search_with_fuzzy(
                'pages', 'test', limit=5, order='name asc, website_id desc, id', options={
                    'displayDescription': False, 'displayDetail': False,
                    'displayExtraDetail': False, 'displayExtraLink': False,
                    'displayImage': False, 'allowFuzzy': True
                }
            )

        test_page = self.env.ref('test_website.test_page')
        test_page.name = 'testTotallyUnique'

        # Editor and Designer see pages in result
        self._autocomplete_page('testTotallyUnique', 1, None)

        test_page.visibility = 'connected'
        self._autocomplete_page('testTotallyUnique', 1, False)
        test_page.visibility = False

        test_page.group_ids = self.env.ref('base.group_public')
        self._autocomplete_page('testTotallyUnique', 1, False)
        test_page.group_ids = False

        # Public user don't see restricted page
        saved_env = self.env
        self.website.env = self.env = self.env(user=self.website.user_id)
        self._autocomplete_page('testTotallyUnique', 0, "Not found")

        test_page.website_indexed = True
        self._autocomplete_page('testTotallyUnique', 1, False)

        test_page.group_ids = self.env.ref('base.group_system')
        self._autocomplete_page('testTotallyUnique', 0, "Not found")

        test_page.group_ids = self.env.ref('base.group_public')
        self._autocomplete_page('testTotallyUnique', 1, False)
        test_page.group_ids = False

        test_page.visibility = 'password'
        self._autocomplete_page('testTotallyUnique', 0, "Not found")

        test_page.visibility = 'connected'
        self._autocomplete_page('testTotallyUnique', 0, "Not found")

        # restore website env for next tests
        self.website.env = self.env = saved_env

    def test_indirect(self):
        self._autocomplete('module', 4, 'model')
        self._autocomplete('rechord', 3, 'record')
        self._autocomplete('suborder', 1, 'submodel')
        # Sub-sub-fields are currently not supported.
        # Adapt expected result if this becomes a feature.
        self._autocomplete('tagg', 0, "Not found")
