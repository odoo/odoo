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

        website = self.env.ref('base.default_website')

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
        cls.website = cls.env.ref('base.default_website')
        cls.WebsiteController = Website()
        cls.options = {}
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
        return cls.env['website.page'].create({
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
            for result in suggestions['results'].get("website_page", {}).get('data', []):
                self.assertEqual("description", result['_icon'], "Expect an fa icon")
                for field in suggestions['parts'].keys():
                    value = result.get(field)
                    if value:
                        self.assertTrue(
                            isinstance(value, Markup),
                            f"All fields should be wrapped in Markup: found {type(value)}: '{value}' in {field}"
                        )
            return suggestions

    def _check_highlight(self, term, value):
        """ Verifies if a term is highlighted in a value """
        self.assertTrue(f'<span class="o_search_matching_text text-body position-relative">{term}</span>' in value.lower(),
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

    def _website_env(self):
        """ Provides an env carrying the 'website_id' context key that `env.website` relies on """
        return self.website.with_context(website_id=self.website.id)

    def _search_detail(self, with_tag_field=False):
        """ Builds `website.page`'s search detail, optionally extended with a tag-like field """
        website = self._website_env()
        search_detail = website.env['website.page']._search_get_detail(website, 'name asc', {})
        if with_tag_field:
            search_detail['search_fields'] = [*search_detail['search_fields'], 'menu_ids.name']
        return search_detail

    def _ranked_urls(self, term, limit=20, with_tag_field=False):
        """ Runs the real ranked search path and returns the resulting URLs """
        _count, results = self._website_env()._search_ranked([self._search_detail(with_tag_field)], term, 0, limit)
        return results[0]['results'].mapped('url')

    def test_relevance_order(self):
        """ Tests the relevance order of `_search_ranked()`'s SQL ranking """
        filler_x, filler_y = 'x ' * 20, 'y ' * 20
        big_x, big_y = 'x ' * 200, 'y ' * 200
        self._create_page('alpha beta gamma', '', '/distance-title-best')
        self._create_page('alphas beta gamma', '', '/distance-title-best-with-unperfect')
        self._create_page('alpha x beta y gamma', '', '/distance-title-mid')
        self._create_page('alpha beta', '', '/one-word-missing-title')
        self._create_page(f'alpha {filler_x}beta {filler_y}gamma', '', '/distance-title-far')
        self._create_page(f'alpha {filler_x}gamma', '', '/distance-title-far-missing')
        self._create_page('generic result', f'{big_x}alpha beta gamma {big_y}', '/distance-desc-best')
        self._create_page('generic result', f'{big_x}beta alpha gamma {big_y}', '/distance-desc-best-disordered')
        self._create_page('generic result', f'{big_x}alpha xxxxxx beta xxxxxx gamma {big_y}', '/distance-desc-mid')
        self._create_page('alpha beta', f'{big_x}alpha beta gamma {big_y}', '/distance-desc-best-missing-title')
        tagged = self._create_page('alpha beta', '', '/one-word-missing-title-with-tag')
        self.env['website.menu'].create({'name': 'gamma', 'page_id': tagged.id})

        self.assertEqual(
            [
                '/distance-title-best',
                '/distance-title-mid',
                '/distance-title-far',
                '/distance-desc-best-missing-title',
                '/distance-desc-best',
                '/distance-desc-best-disordered',
                '/distance-desc-mid',
                '/distance-title-best-with-unperfect',
                '/one-word-missing-title-with-tag',
                '/one-word-missing-title',
                '/distance-title-far-missing',
            ],
            self._ranked_urls('alpha beta gamma', with_tag_field=True),
            "The results order is not correct.",
        )

    def test_relevance_single_word_priority_name_tag_description(self):
        """ For a single-word search, name matches rank above tag matches, which rank above description matches """
        self._create_page('zzunique result', '', '/name-hit')
        tagged = self._create_page('generic result', '', '/tag-hit')
        self.env['website.menu'].create({'name': 'zzunique featured', 'page_id': tagged.id})
        self._create_page('generic result', 'zzunique appears in description only', '/desc-hit')

        self.assertEqual(
            ['/name-hit', '/tag-hit', '/desc-hit'],
            self._ranked_urls('zzunique', with_tag_field=True),
            "Single-word search should prioritize name matches before tags, then description.",
        )

    def test_relevance_three_term_proximity(self):
        """ Among results matching every search term, tighter proximity between the terms ranks higher """
        filler_x, filler_y = 'x ' * 20, 'y ' * 20
        self._create_page('alpha beta gamma', '', '/distance-best')
        self._create_page('alpha x beta y gamma', '', '/distance-mid')
        self._create_page(f'alpha {filler_x}beta {filler_y}gamma', '', '/distance-far')

        self.assertEqual(
            ['/distance-best', '/distance-mid', '/distance-far'],
            self._ranked_urls('alpha beta gamma'),
            "For 3-word searches, closer term proximity should rank higher.",
        )

    def test_relevance_missing_terms_rank_lower(self):
        """ A result matching every search term ranks above one matching only some of them """
        self._create_page('alpha beta gamma', '', '/all-terms-best')
        self._create_page('alpha beta', '', '/missing-one')

        self.assertEqual(
            ['/all-terms-best', '/missing-one'],
            self._ranked_urls('alpha beta gamma'),
            "Results containing all terms must rank before those missing terms.",
        )

    def test_relevance_global_limit_is_global(self):
        """ The global `limit` must cap the TOTAL result count across all `search_details` together """
        for i in range(5):
            self._create_page(f'alpha x{i} beta y{i} gamma', '', f'/bucket-a-{i}')
        for i in range(5):
            self._create_page(f'alpha x{i} beta y{i} gamma', '', f'/bucket-b-{i}')
        best = self._create_page('alpha beta gamma', '', '/bucket-b-best')

        detail_a = self._search_detail()
        detail_a['base_domain'] = [*detail_a['base_domain'], [('url', '=like', '/bucket-a-%')]]
        detail_b = self._search_detail()
        detail_b['base_domain'] = [*detail_b['base_domain'], [('url', '=like', '/bucket-b-%')]]

        _count, results = self._website_env()._search_ranked([detail_a, detail_b], 'alpha beta gamma', 0, 3)
        urls = [url for search_detail in results for url in search_detail['results'].mapped('url')]
        self.assertEqual(len(urls), 3, "the global limit must cap the total across both branches, not each one")
        self.assertIn(best.url, urls, "the single best result must survive the global limit")

    def test_relevance_proportionate_allocation(self):
        """ `_search_apply_proportionate_allocation()` must distribute a global `limit` across groups proportionally """
        for i in range(2):
            self._create_page(f'alpha x{i} beta y{i} gamma', '', f'/bucket-a-{i}')
        for i in range(30):
            self._create_page(f'alpha x{i} beta y{i} gamma', '', f'/bucket-b-{i}')

        detail_a = self._search_detail()
        detail_a['base_domain'] = [*detail_a['base_domain'], [('url', '=like', '/bucket-a-%')]]
        detail_b = self._search_detail()
        detail_b['base_domain'] = [*detail_b['base_domain'], [('url', '=like', '/bucket-b-%')]]

        limit = 10
        count, results = self._website_env()._search_ranked(
            [detail_a, detail_b], 'alpha beta gamma', 0, limit, per_model_limit=True,
        )
        self.assertEqual(count, 32, "the exact per-model counts must still be reported, unlimited")
        self.assertEqual(len(results[0]['results']), 2)
        self.assertEqual(len(results[1]['results']), limit)

        self.WebsiteController._search_apply_proportionate_allocation(results, limit)
        self.assertEqual(len(results[0]['results']), 2, "ceil(2/12 * 10) = 2, unaffected")
        self.assertEqual(len(results[1]['results']), 9, "ceil(10/12 * 10) = 9, truncated by one")

    def test_relevance_large_html_does_not_break_the_union(self):
        """ A >1MB html field must not break the ranking query """
        # The filler must be varied (not just repeated) since a repeated
        # token packs small in a tsvector and would never hit the cap.
        filler = ' '.join(f'filler{i}' for i in range(150000))
        big_description = f'floccinaucinihilipilification {filler}'
        self._create_page('Big page', big_description, '/big-page')
        self._create_page('Other page', 'unrelated content', '/other-page')

        self.assertEqual(['/big-page'], self._ranked_urls('floccinaucinihilipilification'))

    def test_01_few_results(self):
        """ Tests an autocomplete with exact match and less than the maximum number of results """
        suggestions = self._autocomplete("few")
        results = suggestions['results'].get("website_page", {}).get('data', [])
        self.assertEqual(2, suggestions['results_count'], "Text data contains two pages with 'few'")
        self.assertEqual(2, len(results), "All results must be present")
        self.assertFalse(suggestions['fuzzy_search'], "Expects an exact match")
        for result in results:
            self._check_highlight("few", result['name'])

    def test_02_many_results(self):
        """ Tests an autocomplete with exact match and more than the maximum number of results """
        suggestions = self._autocomplete("many")
        results = suggestions['results'].get("website_page", {}).get('data', [])
        self.assertEqual(6, suggestions['results_count'], "Test data contains six pages with 'many'")
        self.assertEqual(6, len(results), "Results must be limited to 6")
        self.assertFalse(suggestions['fuzzy_search'], "Expects an exact match")
        for result in results:
            self._check_highlight("many", result['name'])

    def test_03_no_result(self):
        """ Tests an autocomplete without matching results """
        suggestions = self._autocomplete("nothing")
        results = suggestions['results'].get("website_page", {}).get('data', [])
        self.assertEqual(0, suggestions['results_count'], "Text data contains no page with 'nothing'")
        self.assertEqual(0, len(results), "No result must be present")

    def test_04_fuzzy_results(self):
        """ Tests an autocomplete with fuzzy matching results """
        suggestions = self._autocomplete("appoximtly")
        results = suggestions['results'].get("website_page", {}).get('data', [])
        self.assertEqual("approximately", suggestions['fuzzy_search'], "")
        self.assertEqual(1, suggestions['results_count'], "Text data contains one page with 'approximately'")
        self.assertEqual(1, len(results), "Single result must be present")
        for result in results:
            self._check_highlight("approximately", result['name'])

    def test_05_long_url(self):
        """ Ensures that long URL do not get truncated """
        url = "/this-url-is-so-long-it-would-be-truncated-without-the-fix"
        self._create_page("Too long", "Way too long URL", url)
        suggestions = self._autocomplete("long url")
        results = suggestions['results'].get("website_page", {}).get('data', [])
        self.assertEqual(1, suggestions['results_count'], "Text data contains one page with 'long url'")
        self.assertEqual(1, len(results), "Single result must be present")
        self.assertEqual(url, results[0]['website_url'], 'URL must not be truncated')

    def test_06_case_insensitive_results(self):
        """ Tests an autocomplete with exact match and more than the maximum
        number of results.
        """
        suggestions = self._autocomplete("Many")
        results = suggestions['results'].get("website_page", {}).get('data', [])
        self.assertEqual(6, suggestions['results_count'], "Test data contains six pages with 'Many'")
        self.assertEqual(6, len(results), "Results must be limited to 6")
        self.assertFalse(suggestions['fuzzy_search'], "Expects an exact match")
        for result in results:
            self._check_highlight("many", result['name'])

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
        results = suggestions['results'].get("website_page", {}).get('data', [])
        self.assertEqual(1, len(results), "All results must be present")
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
