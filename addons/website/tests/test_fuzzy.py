# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from lxml import etree
from markupsafe import Markup

import odoo.tests
from odoo.tests.common import TransactionCase

from odoo.addons.website.controllers.main import Website
from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website.tools import distance

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
        self.assertTrue(f'<span class="text-primary-emphasis">{term}</span>' in value.lower(),
                        "Term must be highlighted")

    def test_shorten_around_match(self):
        shorten_around_match = self.WebsiteController._shorten_around_match

        self.assertEqual(
            shorten_around_match("hello world", "world", 100),
            "hello world",
            "Should return original text when it fits within max width"
        )
        self.assertEqual(
            shorten_around_match("aaa bbb ccc", "zzz", 12),
            "aaa bbb ccc",
            "Should return original text when keyword not found and no shortening needed"
        )
        self.assertEqual(
            shorten_around_match("AAA bbb CCC ddd", "ccc", 12),
            "...bb CCC...",
            "Should match keyword ignoring case and center around it"
        )
        self.assertEqual(
            shorten_around_match("aaa bbb ccc ddd", "b c", 12, ",,,"),
            ",,, bbb c,,,",
            "Should use custom placeholder in returned shortened text"
        )
        self.assertEqual(
            shorten_around_match("aaa bbb ccc ddd", "ddd", 12),
            "...b ccc ddd",
            "Should center around match near end while respecting max width"
        )
        self.assertEqual(
            shorten_around_match("hello world", "hello", 8),
            "hello...",
            "Should shorten from end when match is at beginning and text is too long"
        )
        self.assertEqual(
            shorten_around_match("aaa bbb ccc bbb ddd", "bbb", 14),
            "aaa bbb ccc..."
        )
        self.assertEqual(
            shorten_around_match(
                "The quick brown fox jumps over the lazy dog and runs away",
                "fox runs",
                20
            ),
            "... brown fox jum...",
            "Should center around first token 'fox' when exact phrase 'fox runs' not found"
        )

    def test_sort_results_by_relevance(self):
        """Ensure relevance sorting handles source priority and proximity."""
        sort_results = self.WebsiteController._sort_results_by_relevance

        def _result(name, website_url, description_text='', tag_ids=None, desc_field_name='description', model=None):
            data = {
                'name': name,
                'website_url': website_url,
                'tag_ids': tag_ids or [],
                '_mapping': {
                    'description': {
                        'html': True,
                        'match': True,
                        'name': desc_field_name,
                        'type': 'text',
                    },
                },
                desc_field_name: description_text,
            }
            if model is not None:
                data['model'] = model
            return data

        def _urls(records):
            return [record['website_url'] for record in records]

        # 1/ Single-word priority: name > tag > description.
        single_word_results = [
            _result(name='one result', website_url='/name-hit', desc_field_name='description'),
            _result(name='generic result', website_url='/tag-hit', tag_ids=[{'name': 'one featured'}], desc_field_name='content'),
            _result(name='generic result', website_url='/desc-hit', description_text='one appears in description only', desc_field_name='arch'),
        ]
        ordered_single_word = sort_results(list(reversed(single_word_results)), 'one')
        self.assertEqual(
            ['/name-hit', '/tag-hit', '/desc-hit'],
            _urls(ordered_single_word),
            "Single-word search should prioritize name matches before tags, then description.",
        )

        # 2/ Multi-word (3 terms): best proximity should rank first.
        multi_word_results = [
            _result(name='alpha beta gamma', website_url='/distance-best', desc_field_name='content'),
            _result(name='alpha x beta y gamma', website_url='/distance-mid', desc_field_name='arch'),
            _result(name='alpha ' + 'x ' * 20 + 'beta ' + 'y ' * 20 + 'gamma', website_url='/distance-far', desc_field_name='description'),
        ]
        ordered_multi_word = sort_results(list(reversed(multi_word_results)), 'alpha beta gamma')
        self.assertEqual(
            ['/distance-best', '/distance-mid', '/distance-far'],
            _urls(ordered_multi_word),
            "For 3-word searches, closer term proximity should rank higher.",
        )

        # 3/ Multi-word with missing words: complete matches first, then fewer missing terms.
        missing_word_results = [
            _result(name='alpha beta gamma', website_url='/all-terms-best', desc_field_name='arch'),
            _result(name='alpha x beta y gamma', website_url='/all-terms-far', desc_field_name='description'),
            _result(name='alpha beta', website_url='/missing-one', desc_field_name='content'),
            _result(name='alpha', website_url='/missing-two', desc_field_name='arch'),
        ]
        ordered_missing_words = sort_results(list(reversed(missing_word_results)), 'alpha beta gamma')
        self.assertEqual(
            ['/all-terms-best', '/all-terms-far', '/missing-one', '/missing-two'],
            _urls(ordered_missing_words),
            "Results containing all terms must rank before those missing terms.",
        )

        # 4/ sort_by_model=True: results should be grouped by model order.
        grouped_by_model_results = [
            _result(name='one top result', website_url='/m1-top', desc_field_name='description', model='model 1'),
            _result(name='someone second result', website_url='/m2-top', desc_field_name='content', model='model 2'),
            _result(name='generic', website_url='/m1-desc', description_text='one appears here', desc_field_name='arch', model='model 1'),
            _result(name='generic', website_url='/m2-desc', description_text='one appears here too', desc_field_name='description', model='model 2'),
            _result(name='generic', website_url='/m2-missing', description_text='no hit', desc_field_name='content', model='model 2'),
        ]
        ordered_grouped_by_model = sort_results(list(reversed(grouped_by_model_results)), 'one', sort_by_model=True)
        self.assertEqual(
            ['/m1-top', '/m1-desc', '/m2-desc', '/m2-top', '/m2-missing'],
            _urls(ordered_grouped_by_model),
            "With sort_by_model enabled, results should be grouped by model while preserving intra-model relevance order.",
        )

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

    def test_10_multiple_word_search(self):
        """ Ensures partial word match is used when search contains multiple words """
        suggestions = self._autocomplete("results page")
        self.assertEqual(1, suggestions['results_count'], "Test data contains one exact match")
        suggestions = self._autocomplete("results no_match_1")
        self.assertEqual(0, suggestions['results_count'], "Test data contains no exact match")
        suggestions = self._autocomplete("results page no_match")
        self.assertEqual(1, suggestions['results_count'], "Test data contains one exact match")
        suggestions = self._autocomplete("results no_match_1 no_match_2")
        self.assertEqual(0, suggestions['results_count'], "Test data contains no exact match")
