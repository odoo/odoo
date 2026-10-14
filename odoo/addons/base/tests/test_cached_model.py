# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.sql_db import categorize_query
from odoo.tests.common import TransactionCase
from odoo.tools.profiler import Profiler


class TestCachedModel(TransactionCase):
    """ Check the behaviour of ``CachedModel``, through ``res.currency``. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('fr_FR')
        cls.currency = cls.env.ref('base.EUR')
        cls.currency.active = True
        cls.currency.with_context(lang='en_US').currency_unit_label = "Euro"
        cls.currency.with_context(lang='fr_FR').currency_unit_label = "Euro FR"
        cls.currency_en = cls.currency.with_context(lang='en_US')
        cls.currency_fr = cls.currency.with_context(lang='fr_FR')

    def _reset_caches(self):
        self.env.flush_all()
        self.env.transaction.clear()
        self.env.transaction.invalidate_ormcache('stable')

    def _count_currency_queries(self, func):
        """ Return how many queries ``func`` runs on the currency table. """
        with Profiler(collectors=['sql'], db=False) as profiler:
            func()
        return sum(
            categorize_query(entry['full_query'])[1] == 'res_currency'
            for entry in profiler.collectors[0].entries
        )

    def test_cached_data_holds_every_language(self):
        """ A single cache entry serves every language of a translated field. """
        self._reset_caches()
        self.assertEqual(self.currency_en.currency_unit_label, "Euro")
        # the other language is in the same cache entry: no extra query
        self.assertEqual(
            self._count_currency_queries(
                lambda: self.assertEqual(self.currency_fr.currency_unit_label, "Euro FR")
            ),
            0,
        )

        # and the other way around
        self._reset_caches()
        self.assertEqual(self.currency_fr.currency_unit_label, "Euro FR")
        self.assertEqual(
            self._count_currency_queries(
                lambda: self.assertEqual(self.currency_en.currency_unit_label, "Euro")
            ),
            0,
        )

    def test_cached_data_is_invalidated_on_write(self):
        self._reset_caches()
        self.assertEqual(self.currency_en.currency_unit_label, "Euro")
        self.currency_en.currency_unit_label = "Euro 2"
        self._reset_caches()
        self.assertEqual(self.currency_en.currency_unit_label, "Euro 2")
        self.assertEqual(self.currency_fr.currency_unit_label, "Euro FR")

    def test_cached_data_follows_computed_dependencies(self):
        """ A stored computed field must not be cached before it is recomputed. """
        self._reset_caches()
        self.assertEqual(self.currency.decimal_places, 2)
        self.currency.rounding = 0.001
        self.assertEqual(self.currency.rounding, 0.001)
        self.assertEqual(self.currency.decimal_places, 3)
        self.env.invalidate_all()
        self.assertEqual(self.currency.decimal_places, 3)
