# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from lxml import etree
import re
from markupsafe import Markup

from odoo.addons.website.controllers.main import Website
from odoo.addons.website.tools import distance, MockRequest
import odoo.tests
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


@odoo.tests.tagged('-at_install', 'post_install')
class TestFuzzy(TransactionCase):
    def test_01_fuzzy_names(self):
        # Models from other modules commented out on commit: they make the test much longer
        # Last results observed across modules:
        # - 698 words in target dictionary
        # - 21 wrong guesses over 9379 tested typos (0.22%)
        # - Duration: ~5.7 seconds
        fields_per_model = {
            'website.page': ['name', 'arch'],
            # 'product.public.category': ['name', 'website_description'],
            # 'product.template': ['name', 'description_sale'],
            # 'blog.blog': ['name', 'subtitle'],
            # 'blog.post': ['name', 'subtitle'],
            # 'slide.channel': ['name', 'description_short'],
            # 'slide.slide': ['name', 'description'],
            # 'event.event': ['name', 'subtitle'],
        }
        match_pattern = '\\w{4,}'
        words = set()
        for model_name, fields in fields_per_model.items():
            if model_name not in self.env:
                continue
            model = self.env[model_name]
            if 'description' not in fields and 'description' in model:
                fields.append('description')  # larger target dataset
            records = model.sudo().search_read([], fields, limit=100)
            for record in records:
                for field, value in record.items():
                    if isinstance(value, str):
                        if field == 'arch':
                            view_arch = etree.fromstring(value.encode('utf-8'))
                            value = ' '.join(view_arch.itertext())
                        for word in re.findall(match_pattern, value):
                            words.add(word.lower())
        _logger.info("%s words in target dictionary", len(words))

        website = self.env.ref('website.default_website')

        typos = {}

        def add_typo(expected, typo):
            if typo not in words:
                typos.setdefault(typo, set()).add(expected)

        for search in words:
            for index in range(2, len(search)):
                # swap letters
                if search[index] != search[index - 1]:
                    add_typo(search, search[:index - 1] + search[index] + search[index - 1] + search[index + 1:])
                # miss letter
                if len(search) > 4:
                    add_typo(search, search[:index - 1] + search[index:])
                # wrong letter
                add_typo(search, search[:index - 1] + '!' + search[index:])

        words = list(words)
        words.sort()  # guarantee results stability
        mismatch_count = 0
        for search, expected in typos.items():
            fuzzy_guess = website._search_find_fuzzy_term({}, search, word_list=words)
            if not fuzzy_guess or (fuzzy_guess not in expected and fuzzy_guess not in [exp[:-1] for exp in expected]):
                mismatch_count += 1
                _logger.info("'%s' fuzzy matched to '%s' instead of %s", search, fuzzy_guess, expected)

        ratio = 100.0 * mismatch_count / len(typos)
        _logger.info("%s wrong guesses over %s tested typos (%.2f%%)", mismatch_count, len(typos), ratio)
        typos.clear()
        words.clear()
        self.assertTrue(ratio < 1, "Too many wrong fuzzy guesses")

    def test_02_distance(self):
        self.assertEqual(distance("gravity", "granity", 3), 1)
        self.assertEqual(distance("gravity", "graity", 3), 1)
        self.assertEqual(distance("gravity", "grait", 3), 2)
        self.assertEqual(distance("gravity", "griaty", 3), 3)
        self.assertEqual(distance("gravity", "giraty", 3), 3)
        self.assertEqual(distance("gravity", "giraty", 2), -1)
        self.assertEqual(distance("gravity", "girafe", 3), -1)
        self.assertEqual(distance("warranty", "warantl", 3), 2)

        # non-optimized cases still have to return correct results
        self.assertEqual(distance("warranty", "warranty", 3), 0)
        self.assertEqual(distance("", "warranty", 3), -1)
        self.assertEqual(distance("", "warranty", 10), 8)
        self.assertEqual(distance("warranty", "", 10), 8)
        self.assertEqual(distance("", "", 10), 0)


@odoo.tests.tagged('-at_install', 'post_install')
class TestAutoComplete(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].browse(1)
        cls.WebsiteController = Website()
        cls.options = {
            'displayDescription': True,
        }
        cls.expectedParts = {
            'name': True,
            'description': True,
            'website_url': True,
        }
        texts = [
            "This page only matches few",
            "This page matches both few and many",
            "This page only matches many",
            "Many results contain this page",
            "How many times does the word many appear",
            "Will there be many results",
            "Welcome to our many friends next week-end",
            "This should only be approximately matched",
        ]
        for text in texts:
            cls._create_page(text, text, f"/{text.lower().replace(' ', '-')}")

    @classmethod
    def _create_page(cls, name, content, url):
        cls.env['website.page'].create({
            'name': name,
            'type': 'qweb',
            'arch': f'<div>{content}</div>',
            'url': url,
            'is_published': True,
        })

    def _autocomplete(self, term):
        """ Calls the autocomplete for a given term and performs general checks """
        with MockRequest(self.env, website=self.website):
            suggestions = self.WebsiteController.autocomplete(
                search_type="pages", term=term, max_nb_chars=50, options=self.options,
            )
            if suggestions['results_count']:
                self.assertDictEqual(self.expectedParts, suggestions['parts'],
                                     f"Parts should contain {self.expectedParts.keys()}")
            for result in suggestions['results']:
                self.assertEqual("fa-file-o", result['_fa'], "Expect an fa icon")
                for field in suggestions['parts'].keys():
                    value = result[field]
                    if value:
                        self.assertTrue(
                            isinstance(value, Markup),
                            f"All fields should be wrapped in Markup: found {type(value)}: '{value}' in {field}"
                        )
            return suggestions

    def _check_highlight(self, term, value):
        """ Verifies if a term is highlighted in a value """
        self.assertTrue(f'<span class="text-primary">{term}</span>' in value.lower(),
                        "Term must be highlighted")

    def test_01_few_results(self):
        """ Tests an autocomplete with exact match and less than the maximum number of results """
        suggestions = self._autocomplete("few")
        self.assertEqual(2, suggestions['results_count'], "Text data contains two pages with 'few'")
        self.assertEqual(2, len(suggestions['results']), "All results must be present")
        self.assertFalse(suggestions['fuzzy_search'], "Expects an exact match")
        for result in suggestions['results']:
            self._check_highlight("few", result['name'])
            self._check_highlight("few", result['description'])

    def test_02_many_results(self):
        """ Tests an autocomplete with exact match and more than the maximum number of results """
        suggestions = self._autocomplete("many")
        self.assertEqual(6, suggestions['results_count'], "Test data contains six pages with 'many'")
        self.assertEqual(5, len(suggestions['results']), "Results must be limited to 5")
        self.assertFalse(suggestions['fuzzy_search'], "Expects an exact match")
        for result in suggestions['results']:
            self._check_highlight("many", result['name'])
            self._check_highlight("many", result['description'])

    def test_03_no_result(self):
        """ Tests an autocomplete without matching results """
        suggestions = self._autocomplete("nothing")
        self.assertEqual(0, suggestions['results_count'], "Text data contains no page with 'nothing'")
        self.assertEqual(0, len(suggestions['results']), "No result must be present")

    def test_04_fuzzy_results(self):
        """ Tests an autocomplete with fuzzy matching results """
        suggestions = self._autocomplete("appoximtly")
        self.assertEqual("approximately", suggestions['fuzzy_search'], "")
        self.assertEqual(1, suggestions['results_count'], "Text data contains one page with 'approximately'")
        self.assertEqual(1, len(suggestions['results']), "Single result must be present")
        for result in suggestions['results']:
            self._check_highlight("approximately", result['name'])
            self._check_highlight("approximately", result['description'])

    def test_05_long_url(self):
        """ Ensures that long URL do not get truncated """
        url = "/this-url-is-so-long-it-would-be-truncated-without-the-fix"
        self._create_page("Too long", "Way too long URL", url)
        suggestions = self._autocomplete("long url")
        self.assertEqual(1, suggestions['results_count'], "Text data contains one page with 'long url'")
        self.assertEqual(1, len(suggestions['results']), "Single result must be present")
        self.assertEqual(url, suggestions['results'][0]['website_url'], 'URL must not be truncated')

    def test_06_case_insensitive_results(self):
        """ Tests an autocomplete with exact match and more than the maximum
        number of results.
        """
        suggestions = self._autocomplete("Many")
        self.assertEqual(6, suggestions['results_count'], "Test data contains six pages with 'Many'")
        self.assertEqual(5, len(suggestions['results']), "Results must be limited to 5")
        self.assertFalse(suggestions['fuzzy_search'], "Expects an exact match")
        for result in suggestions['results']:
            self._check_highlight("many", result['name'])
            self._check_highlight("many", result['description'])

    def test_07_no_fuzzy_for_mostly_number(self):
        """ Ensures exact match is used when search contains mostly numbers. """
        self._create_page('Product P7935432254U7 page', 'Product P7935432254U7 kangaroo shoes', '/numberpage')
        suggestions = self._autocomplete("54321")
        self.assertEqual(0, suggestions['results_count'], "Test data contains no exact match")
        suggestions = self._autocomplete("54322")
        self.assertEqual(1, suggestions['results_count'], "Test data contains one exact match")
        suggestions = self._autocomplete("P79355")
        self.assertEqual(0, suggestions['results_count'], "Test data contains no exact match")
        suggestions = self._autocomplete("P79354")
        self.assertEqual(1, suggestions['results_count'], "Test data contains one exact match")
        self.assertFalse(suggestions['fuzzy_search'], "Expects an exact match")
        suggestions = self._autocomplete("kangroo") # must contain a typo
        self.assertEqual(1, suggestions['results_count'], "Test data contains one fuzzy match")
        self.assertTrue(suggestions['fuzzy_search'], "Expects a fuzzy match")

    def test_08_fuzzy_classic_numbers(self):
        """ Ensures fuzzy match is used when search contains a few numbers. """
        self._create_page('iPhone 6', 'iPhone6', '/iphone6')
        suggestions = self._autocomplete("iphone7")
        self.assertEqual(1, suggestions['results_count'], "Test data contains one fuzzy match")
        self.assertTrue(suggestions['fuzzy_search'], "Expects an fuzzy match")

    def test_09_hyphen(self):
        """ Ensures that hyphen is considered part of word """
        suggestions = self._autocomplete("weekend")
        self.assertEqual(1, suggestions['results_count'], "Text data contains one page with 'weekend'")
        self.assertEqual('week-end', suggestions['fuzzy_search'], "Expects a fuzzy match")
        suggestions = self._autocomplete("week-end")
        self.assertEqual(1, len(suggestions['results']), "All results must be present")
        self.assertFalse(suggestions['fuzzy_search'], "Expects an exact match")
