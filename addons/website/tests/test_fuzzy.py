import logging
import re

from lxml import etree
from markupsafe import Markup

import odoo.tests
from odoo.tests.common import TransactionCase, new_test_user

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website.controllers.main import Website
from odoo.addons.website.tools import distance, similarity_score, text_from_html

_logger = logging.getLogger(__name__)


@odoo.tests.tagged("-at_install", "post_install")
class TestFuzzy(TransactionCase):
    def _trigram_words(self, records, fields, term="mariglod", limit=1):
        detail = {
            "model": records._name,
            "search_fields": fields,
            "base_domain": [[("id", "in", records.ids)]],
        }
        words = set(
            records.env.ref("website.default_website")._trigram_enumerate_words(
                [detail], term, limit
            )
        )
        _logger.debug(
            "Trigram fields=%s eligible=%s words=%s", fields, records.ids, words
        )
        return words

    def test_trigram_filters_before_candidate_limit(self):
        eligible = self.env["res.partner"].create({"name": "marigold"})
        self.env["res.partner"].create({"name": "mariglod"})
        self.assertIn("marigold", self._trigram_words(eligible, ["name"]))

    def test_trigram_applies_record_rules_before_candidate_limit(self):
        user = new_test_user(self.env, login="fuzzy_reader", groups="base.group_user")
        eligible = self.env["res.partner"].create({"name": "marigold"})
        excluded = self.env["res.partner"].create({"name": "mariglod"})
        self.env["ir.rule"].create(
            {
                "name": "Fuzzy candidate access regression",
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "domain_force": repr([("id", "!=", excluded.id)]),
            }
        )
        records = (eligible | excluded).with_user(user)
        self.assertIn("marigold", self._trigram_words(records, ["name"]))
        self.assertIn("mariglod", self._trigram_words(records.sudo(), ["name"]))

    def test_trigram_flushes_pending_search_values(self):
        eligible = self.env["res.partner"].create({"name": "unrelated"})
        self.env.flush_all()
        eligible.name = "marigold"
        self.assertIn("marigold", self._trigram_words(eligible, ["name"]))

    def test_trigram_indirect_only_one2many(self):
        parent = self.env["res.partner"].create({"name": "Parent"})
        self.env["res.partner"].create({"name": "marigold", "parent_id": parent.id})
        self.assertEqual({"marigold"}, self._trigram_words(parent, ["child_ids.name"]))

    def test_trigram_relation_domain_applies_before_limit(self):
        parents = self.env["res.partner"].create(
            [{"name": "Eligible parent"}, {"name": "Excluded child parent"}]
        )
        self.env["res.partner"].create(
            [
                {"name": "marigold", "parent_id": parents[0].id},
                {"name": "mariglod", "parent_id": parents[1].id, "active": False},
            ]
        )
        self.assertFalse(parents[1].child_ids)
        self.assertIn("marigold", self._trigram_words(parents, ["child_ids.name"]))

    def test_trigram_many2one_keeps_archived_target(self):
        parent = self.env["res.partner"].create({"name": "marigold", "active": False})
        child = self.env["res.partner"].create(
            {"name": "Child", "parent_id": parent.id}
        )
        self.assertEqual(child.parent_id, parent)
        self.assertIn("marigold", self._trigram_words(child, ["parent_id.name"]))

    def test_trigram_many2many_respects_active_context(self):
        tags = self.env["res.partner.tag"].create(
            [
                {"name": "marigold"},
                {"name": "mariglod", "active": False},
            ]
        )
        partners = self.env["res.partner"].create(
            [
                {"name": name, "tag_ids": [(6, 0, tag.ids)]}
                for name, tag in zip(("Visible", "Hidden"), tags, strict=True)
            ]
        )
        self.assertFalse(partners[1].tag_ids)
        self.assertIn("marigold", self._trigram_words(partners, ["tag_ids.name"]))
        self.assertIn(
            "mariglod",
            self._trigram_words(
                partners.with_context(active_test=False), ["tag_ids.name"]
            ),
        )

    def test_trigram_indirect_only_many2many(self):
        tag = self.env["res.partner.tag"].create({"name": "marigold"})
        partner = self.env["res.partner"].create({"name": "Tagged"})
        partner.tag_ids = tag
        self.assertEqual({"marigold"}, self._trigram_words(partner, ["tag_ids.name"]))

    def test_basic_indirect_search_uses_only_selected_fields(self):
        parent = self.env["res.partner"].create({"name": "marathon"})
        self.env["res.partner"].create({"name": "marigold", "parent_id": parent.id})
        detail = {
            "model": "res.partner",
            "search_fields": ["child_ids.name"],
            "base_domain": [[("id", "=", parent.id)]],
        }
        words = set(
            self.env.ref("website.default_website")._basic_enumerate_words(
                [detail], "mariglod", 1
            )
        )
        _logger.debug("Basic indirect-only candidates=%s", words)
        self.assertEqual(words, {"marigold"})

    def test_trigram_flushes_pending_relation(self):
        parent = self.env["res.partner"].create({"name": "marigold"})
        child = self.env["res.partner"].create({"name": "Child"})
        self.env.flush_all()
        child.parent_id = parent
        self.assertIn("marigold", self._trigram_words(child, ["parent_id.name"]))

    def test_trigram_distinct_relations_to_same_model(self):
        parent = self.env["res.partner"].create({"name": "marigold"})
        child = self.env["res.partner"].create(
            {"name": "Child", "parent_id": parent.id}
        )
        self.env["res.partner"].create({"name": "unrelated", "parent_id": child.id})
        self.assertIn(
            "marigold",
            self._trigram_words(child, ["name", "parent_id.name", "child_ids.name"]),
        )

    def test_01_fuzzy_names(self):
        fields_per_model = {
            "website.page": ["name", "arch"],
        }
        match_pattern = "\\w{4,}"
        words = set()
        for model_name, fields in fields_per_model.items():
            if model_name not in self.env:
                continue
            model = self.env[model_name]
            if "description" not in fields and "description" in model:
                fields.append("description")
            records = model.sudo().search_read([], fields, limit=100)
            for record in records:
                for field, value in record.items():
                    if isinstance(value, str):
                        if field == "arch":
                            view_arch = etree.fromstring(value.encode("utf-8"))
                            value = " ".join(view_arch.itertext())
                        words.update(
                            word.lower() for word in re.findall(match_pattern, value)
                        )
        _logger.info("%s words in target dictionary", len(words))

        website = self.env.ref("website.default_website")

        typos = {}

        def add_typo(expected, typo):
            if typo not in words:
                typos.setdefault(typo, set()).add(expected)

        for search in words:
            for index in range(2, len(search)):
                if search[index] != search[index - 1]:
                    add_typo(
                        search,
                        search[: index - 1]
                        + search[index]
                        + search[index - 1]
                        + search[index + 1 :],
                    )
                if len(search) > 4:
                    add_typo(search, search[: index - 1] + search[index:])
                add_typo(search, search[: index - 1] + "!" + search[index:])

        words = list(words)
        words.sort()
        mismatch_count = 0
        for search, expected in typos.items():
            fuzzy_guess = website._search_find_fuzzy_term({}, search, word_list=words)
            if not fuzzy_guess or (
                fuzzy_guess not in expected
                and fuzzy_guess not in [exp[:-1] for exp in expected]
            ):
                mismatch_count += 1
                _logger.info(
                    "'%s' fuzzy matched to '%s' instead of %s",
                    search,
                    fuzzy_guess,
                    expected,
                )

        ratio = 100.0 * mismatch_count / len(typos)
        _logger.info(
            "%s wrong guesses over %s tested typos (%.2f%%)",
            mismatch_count,
            len(typos),
            ratio,
        )
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

        self.assertEqual(distance("warranty", "warranty", 3), 0)
        self.assertEqual(distance("", "warranty", 3), -1)
        self.assertEqual(distance("", "warranty", 10), 8)
        self.assertEqual(distance("warranty", "", 10), 8)
        self.assertEqual(distance("", "", 10), 0)

    def test_03_similarity_score_empty_operand(self):
        self.assertEqual(similarity_score("", "warranty"), -1)
        self.assertEqual(similarity_score("warranty", ""), -1)
        self.assertEqual(similarity_score("", ""), -1)
        self.assertEqual(similarity_score("gravity", "gravity"), 1.0)


@odoo.tests.tagged("-at_install", "post_install")
class TestFuzzyWordSource(TransactionCase):
    """The fuzzy dictionary is the text a visitor reads, not the markup around it.

    Two enumerators answer the same question -- `_trigram_enumerate_words` on a
    pg_trgm database, `_basic_enumerate_words` everywhere else -- so they must
    return the same words. They did not: only the basic one reduced a page's
    `arch_db` to its text, so on every real deployment a typo was "corrected"
    to a CSS class or a tag name, and the correction then matched no page,
    because the result filter reads the text.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("website.default_website")
        view = cls.env["ir.ui.view"].create(
            {
                "name": "Fuzzy markup page",
                "type": "qweb",
                "key": "website.fuzzy_markup_page",
                "website_id": cls.website.id,
                "arch": """
                    <t t-name="website.fuzzy_markup_page">
                      <div class="zzmarkupclass" data-snippet="zzmarkupattr">
                        <span>zzvisibletext appears in the page</span>
                      </div>
                    </t>
                """,
            }
        )
        cls.page = cls.env["website.page"].create(
            {
                "url": "/fuzzy-markup",
                "view_id": view.id,
                "is_published": True,
                "website_id": cls.website.id,
            }
        )
        cls.detail = cls.env["website.page"]._search_get_detail(
            cls.website,
            "name asc",
            {
                "displayDescription": True,
                "displayDetail": False,
                "displayExtraDetail": False,
                "displayExtraLink": False,
                "displayImage": False,
            },
        )
        cls.detail["base_domain"] = [[("id", "=", cls.page.id)]]

    def _words(self, enumerator, term):
        return set(enumerator([dict(self.detail)], term, 1000))

    def test_markup_tokens_are_not_offered_as_corrections(self):
        for name in ("_trigram_enumerate_words", "_basic_enumerate_words"):
            with self.subTest(enumerator=name):
                words = self._words(getattr(self.website, name), "zzvisibletxet")
                self.assertIn("zzvisibletext", words)
                self.assertNotIn("zzmarkupclass", words)
                self.assertNotIn("zzmarkupattr", words)

    def test_the_two_enumerators_agree_on_a_page(self):
        term = "zzvisibletxet"
        self.assertEqual(
            self._words(self.website._trigram_enumerate_words, term),
            self._words(self.website._basic_enumerate_words, term),
        )

    def test_a_correction_the_search_can_honour(self):
        # The banner promises "Results are displayed for X"; X has to be a term
        # the very next search can find, which a class name never is.
        options = {
            "displayDescription": True,
            "displayDetail": False,
            "displayExtraDetail": False,
            "displayExtraLink": False,
            "displayImage": False,
            "allowFuzzy": True,
        }
        # A dropped letter, not a truncation: `search in word` would otherwise
        # answer before the candidate list is even scored.
        count, _results, fuzzy = self.website._search_with_fuzzy(
            "pages", "zzmarkupclss", 5, "name asc", options
        )
        self.assertFalse(
            fuzzy,
            "a token that exists only in the markup must not be offered as a correction",
        )
        self.assertEqual(count, 0)

    def test_a_detail_without_a_mapping_declares_no_html_field(self):
        # `_trigram_words` above builds a bare detail; the html declaration is
        # optional and its absence must not raise.
        self.assertEqual(
            self.env["website"]._search_get_html_fields(
                {"model": "website.page", "search_fields": ["name"], "base_domain": []}
            ),
            frozenset(),
        )


@odoo.tests.tagged("-at_install", "post_install")
class TestTextFromHtml(TransactionCase):
    def test_keeps_text_following_a_stripped_element(self):
        self.assertEqual(
            text_from_html("<svg><path/></svg>text after svg", True),
            "text after svg",
        )
        self.assertEqual(
            text_from_html("intro <script>var x = 1;</script> outro", True),
            "intro outro",
        )
        self.assertEqual(
            text_from_html("before <style>.x{}</style> after", True),
            "before after",
        )
        self.assertEqual(
            text_from_html(
                '<div class="css_non_editable_mode_hidden">hidden</div>visible',
                True,
            ),
            "visible",
        )

    def test_resolves_html_entities(self):
        self.assertEqual(text_from_html("Caf&eacute; Gourmand", True), "Café Gourmand")
        self.assertEqual(text_from_html("word1&nbsp;word2", True), "word1 word2")
        self.assertEqual(text_from_html("&euro;100 &mdash; sale", True), "€100 — sale")
        self.assertEqual(
            text_from_html("Bien s&ucirc;r&nbsp;! &Agrave; demain", True),
            "Bien sûr ! À demain",
        )

    def test_preserved_behaviour(self):
        self.assertEqual(text_from_html("Tom &amp; Jerry", True), "Tom & Jerry")
        self.assertEqual(text_from_html("5 &lt; 6 &gt; 4", True), "5 < 6 > 4")
        self.assertEqual(
            text_from_html("<p>unclosed <b>bold</p>", True), "unclosed bold"
        )
        self.assertEqual(text_from_html("<!-- a comment -->real", True), "real")
        self.assertEqual(text_from_html("plain text"), "plain text")
        self.assertEqual(text_from_html("", True), "")
        self.assertEqual(text_from_html(None, True), "")


@odoo.tests.tagged("-at_install", "post_install")
class TestAutoComplete(TransactionCase):
    def test_render_does_not_fetch_undisplayed_records(self):
        pages = self.env["website.page"].search([], limit=3)
        self.assertEqual(len(pages), 3)
        for limit, count in ((1, 1), (0, 0), (None, 3)):
            with self.subTest(limit=limit):
                pages.invalidate_recordset(["url"])
                results = pages._search_render_results(["url"], {}, "icon", limit)
                cached = [
                    self.env.cache.contains(page, pages._fields["url"])
                    for page in pages
                ]
                _logger.debug(
                    "Limited render limit=%s returned=%s cached=%s",
                    limit,
                    results,
                    cached,
                )
                self.assertEqual(
                    [result["id"] for result in results], pages[:count].ids
                )
                self.assertEqual(cached, [True] * count + [False] * (3 - count))

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env["website"].browse(1)
        cls.WebsiteController = Website()
        cls.options = {
            "displayDescription": True,
        }
        cls.expectedParts = {
            "name": True,
            "description": True,
            "website_url": True,
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
        cls.env["website.page"].create(
            {
                "name": name,
                "type": "qweb",
                "arch": f"<div>{content}</div>",
                "url": url,
                "is_published": True,
            }
        )

    def _autocomplete(self, term):
        with MockRequest(self.env, website=self.website):
            suggestions = self.WebsiteController.autocomplete(
                search_type="pages",
                term=term,
                max_nb_chars=50,
                options=self.options,
            )
            if suggestions["results_count"]:
                self.assertDictEqual(
                    self.expectedParts,
                    suggestions["parts"],
                    f"Parts should contain {self.expectedParts.keys()}",
                )
            for result in suggestions["results"]:
                self.assertEqual(
                    "fa-regular fa-file", result["_fa"], "Expect an fa icon"
                )
                for field in suggestions["parts"]:
                    value = result[field]
                    if value:
                        self.assertTrue(
                            isinstance(value, Markup),
                            f"All fields should be wrapped in Markup: found {type(value)}: '{value}' in {field}",
                        )
            return suggestions

    def _check_highlight(self, term, value):
        self.assertTrue(
            f'<span class="text-primary-emphasis">{term}</span>' in value.lower(),
            "Term must be highlighted",
        )

    def test_01_few_results(self):
        suggestions = self._autocomplete("few")
        self.assertEqual(
            2, suggestions["results_count"], "Text data contains two pages with 'few'"
        )
        self.assertEqual(2, len(suggestions["results"]), "All results must be present")
        self.assertFalse(suggestions["fuzzy_search"], "Expects an exact match")
        for result in suggestions["results"]:
            self._check_highlight("few", result["name"])
            self._check_highlight("few", result["description"])

    def test_02_many_results(self):
        suggestions = self._autocomplete("many")
        self.assertEqual(
            6, suggestions["results_count"], "Test data contains six pages with 'many'"
        )
        self.assertEqual(5, len(suggestions["results"]), "Results must be limited to 5")
        self.assertFalse(suggestions["fuzzy_search"], "Expects an exact match")
        for result in suggestions["results"]:
            self._check_highlight("many", result["name"])
            self._check_highlight("many", result["description"])

    def test_03_no_result(self):
        suggestions = self._autocomplete("nothing")
        self.assertEqual(
            0, suggestions["results_count"], "Text data contains no page with 'nothing'"
        )
        self.assertEqual(0, len(suggestions["results"]), "No result must be present")

    def test_04_fuzzy_results(self):
        suggestions = self._autocomplete("appoximtly")
        self.assertEqual("approximately", suggestions["fuzzy_search"], "")
        self.assertEqual(
            1,
            suggestions["results_count"],
            "Text data contains one page with 'approximately'",
        )
        self.assertEqual(
            1, len(suggestions["results"]), "Single result must be present"
        )
        for result in suggestions["results"]:
            self._check_highlight("approximately", result["name"])
            self._check_highlight("approximately", result["description"])

    def test_05_long_url(self):
        url = "/this-url-is-so-long-it-would-be-truncated-without-the-fix"
        self._create_page("Too long", "Way too long URL", url)
        suggestions = self._autocomplete("long url")
        self.assertEqual(
            1,
            suggestions["results_count"],
            "Text data contains one page with 'long url'",
        )
        self.assertEqual(
            1, len(suggestions["results"]), "Single result must be present"
        )
        self.assertEqual(
            url, suggestions["results"][0]["website_url"], "URL must not be truncated"
        )

    def test_06_case_insensitive_results(self):
        suggestions = self._autocomplete("Many")
        self.assertEqual(
            6, suggestions["results_count"], "Test data contains six pages with 'Many'"
        )
        self.assertEqual(5, len(suggestions["results"]), "Results must be limited to 5")
        self.assertFalse(suggestions["fuzzy_search"], "Expects an exact match")
        for result in suggestions["results"]:
            self._check_highlight("many", result["name"])
            self._check_highlight("many", result["description"])

    def test_07_no_fuzzy_for_mostly_number(self):
        self._create_page(
            "Product P7935432254U7 page",
            "Product P7935432254U7 kangaroo shoes",
            "/numberpage",
        )
        suggestions = self._autocomplete("54321")
        self.assertEqual(
            0, suggestions["results_count"], "Test data contains no exact match"
        )
        suggestions = self._autocomplete("54322")
        self.assertEqual(
            1, suggestions["results_count"], "Test data contains one exact match"
        )
        suggestions = self._autocomplete("P79355")
        self.assertEqual(
            0, suggestions["results_count"], "Test data contains no exact match"
        )
        suggestions = self._autocomplete("P79354")
        self.assertEqual(
            1, suggestions["results_count"], "Test data contains one exact match"
        )
        self.assertFalse(suggestions["fuzzy_search"], "Expects an exact match")
        suggestions = self._autocomplete("kangroo")
        self.assertEqual(
            1, suggestions["results_count"], "Test data contains one fuzzy match"
        )
        self.assertTrue(suggestions["fuzzy_search"], "Expects a fuzzy match")

    def test_08_fuzzy_classic_numbers(self):
        self._create_page("iPhone 6", "iPhone6", "/iphone6")
        suggestions = self._autocomplete("iphone7")
        self.assertEqual(
            1, suggestions["results_count"], "Test data contains one fuzzy match"
        )
        self.assertTrue(suggestions["fuzzy_search"], "Expects an fuzzy match")

    def test_09_hyphen(self):
        suggestions = self._autocomplete("weekend")
        self.assertEqual(
            1,
            suggestions["results_count"],
            "Text data contains one page with 'weekend'",
        )
        self.assertEqual(
            "week-end", suggestions["fuzzy_search"], "Expects a fuzzy match"
        )
        suggestions = self._autocomplete("week-end")
        self.assertEqual(1, len(suggestions["results"]), "All results must be present")
        self.assertFalse(suggestions["fuzzy_search"], "Expects an exact match")
