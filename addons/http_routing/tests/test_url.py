from unittest.mock import MagicMock, Mock, patch

import werkzeug.exceptions
import werkzeug.routing

from odoo.tests import TransactionCase, tagged

from .common import MockRequest, setup_frontend_langs


@tagged("-at_install", "post_install")
class TestUrlCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        fr = cls.env["res.lang"]._activate_lang("fr_FR")
        fr.url_code = "fr"
        en = cls.env.ref("base.lang_en")
        setup_frontend_langs(cls.env, en + fr, en)
        cls.IrHttp = cls.env["ir.http"]
        cls.EP = "/website/translations"


class TestUrlLang(TestUrlCommon):
    def test_adds_context_lang_when_not_default(self):
        with MockRequest(self.env, context={"lang": "fr_FR"}, mock_router=False):
            self.assertEqual(self.IrHttp._url_for(self.EP), "/fr" + self.EP)

    def test_default_context_lang_untouched(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(self.IrHttp._url_for(self.EP), self.EP)

    def test_query_string_preserved(self):
        with MockRequest(self.env, context={"lang": "fr_FR"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_for(self.EP + "?x=1&x=2"),
                "/fr" + self.EP + "?x=1&x=2",
            )

    def test_trailing_slash_dropped_on_insert(self):
        with MockRequest(self.env, context={"lang": "fr_FR"}, mock_router=False):
            self.assertEqual(self.IrHttp._url_for(self.EP + "/"), "/fr" + self.EP)

    def test_force_lang_replaces_existing_lang(self):
        with MockRequest(self.env, context={"lang": "fr_FR"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_for("/fr" + self.EP, "en_US"), "/en" + self.EP
            )

    def test_default_lang_prefix_stripped(self):
        with MockRequest(self.env, context={"lang": "fr_FR"}, mock_router=False):
            self.assertEqual(self.IrHttp._url_for("/en" + self.EP), self.EP)

    def test_never_returns_an_empty_url(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            for url in ("/en", "/fr", "/", "/en/", "/fr/", self.EP):
                with self.subTest(url=url):
                    self.assertTrue(self.IrHttp._url_for(url).startswith("/"))
                    self.assertTrue(self.IrHttp._url_for(url, "en_US").startswith("/"))
                    self.assertTrue(self.IrHttp._url_for(url, "fr_FR").startswith("/"))

    def test_lang_placeholder_passthrough(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_for(self.EP, "[lang]"), "/[lang]" + self.EP
            )

    def test_absolute_url_untouched(self):
        with MockRequest(self.env, context={"lang": "fr_FR"}, mock_router=False):
            url = "https://odoo.com" + self.EP
            self.assertEqual(self.IrHttp._url_for(url), url)

    def test_invalid_url_untouched(self):
        with MockRequest(self.env, context={"lang": "fr_FR"}, mock_router=False):
            self.assertEqual(self.IrHttp._url_for("http://]"), "http://]")

    def test_non_multilang_urls_untouched(self):
        with MockRequest(self.env, context={"lang": "fr_FR"}, mock_router=False):
            self.assertEqual(self.IrHttp._url_for("/web/login"), "/web/login")
            self.assertEqual(
                self.IrHttp._url_for("/foo/static/src/x.js"), "/foo/static/src/x.js"
            )

    def test_fragment_is_not_part_of_the_path(self):
        with MockRequest(self.env, context={"lang": "fr_FR"}, mock_router=False):
            self.assertEqual(self.IrHttp._url_for("/fr#top"), "/fr#top")
            self.assertEqual(
                self.IrHttp._url_for("/fr" + self.EP + "#top"), "/fr" + self.EP + "#top"
            )
            self.assertEqual(
                self.IrHttp._url_for(self.EP + "#top"), "/fr" + self.EP + "#top"
            )
            self.assertEqual(
                self.IrHttp._url_for(self.EP + "#top?a=b"), "/fr" + self.EP + "#top?a=b"
            )
            self.assertEqual(
                self.IrHttp._url_for(self.EP + "?a=b#top"),
                "/fr" + self.EP + "?a=b#top",
            )

    def test_fragment_does_not_defeat_lang_replacement(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_for("/fr" + self.EP + "#top", "en_US"),
                "/en" + self.EP + "#top",
            )
            self.assertEqual(
                self.IrHttp._url_for("/en" + self.EP + "#top", "fr_FR"),
                "/fr" + self.EP + "#top",
            )

    def test_trailing_slash_dropped_by_every_branch(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            slashed, bare = self.EP + "/", self.EP
            for url in (slashed, "/en" + slashed, "/fr" + slashed):
                with self.subTest(url=url):
                    self.assertEqual(self.IrHttp._url_for(url, "fr_FR"), "/fr" + bare)
                    self.assertEqual(self.IrHttp._url_for(url, "en_US"), "/en" + bare)
            self.assertEqual(self.IrHttp._url_for("/en" + slashed), bare)

    def test_root_is_not_mistaken_for_a_trailing_slash(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            for url in ("/", "/en/", "/fr/", "/en", "/fr"):
                with self.subTest(url=url):
                    for lang in (None, "en_US", "fr_FR"):
                        got = (
                            self.IrHttp._url_for(url, lang)
                            if lang
                            else self.IrHttp._url_for(url)
                        )
                        self.assertTrue(got.startswith("/"), got)

    def test_bare_fragment_is_rooted_when_a_language_is_forced(self):
        with MockRequest(
            self.env, path="/mine", context={"lang": "en_US"}, mock_router=False
        ):
            self.assertEqual(self.IrHttp._url_for("#top"), "#top")
            self.assertEqual(self.IrHttp._url_for("#top", "fr_FR"), "/fr/mine#top")
            self.assertEqual(self.IrHttp._url_for("?a=b", "fr_FR"), "/fr/mine?a=b")
            self.assertEqual(
                self.IrHttp._url_localized("#top", lang_code="fr_FR"), "#top"
            )

    def test_falsy_url_does_not_raise(self):
        with MockRequest(self.env, context={"lang": "fr_FR"}, mock_router=False):
            for url in (None, "", False):
                with self.subTest(url=url):
                    self.assertFalse(self.IrHttp._url_for(url))


class TestUrlLangContext(TestUrlCommon):
    def _with_ctx_lang(self, request, value, present=True):
        ctx = dict(request.env.context)
        ctx.pop("lang", None)
        if present:
            ctx["lang"] = value
        request.env = request.env(context=ctx)

    def test_missing_or_falsy_context_lang_does_not_raise(self):
        cases = [("absent", None, False), ("None", None, True), ("False", False, True)]
        for label, value, present in cases:
            with self.subTest(context_lang=label):
                with MockRequest(self.env, mock_router=False) as req:
                    self._with_ctx_lang(req, value, present)
                    url = self.IrHttp._url_for(self.EP)
                self.assertTrue(url.startswith("/"))
                self.assertNotIn("None", url)
                self.assertNotIn("False", url)

    def test_falsy_context_lang_falls_back_to_request_lang(self):
        with MockRequest(self.env, context={"lang": "fr_FR"}, mock_router=False) as req:
            self._with_ctx_lang(req, None, present=True)
            self.assertEqual(self.IrHttp._url_for(self.EP), "/fr" + self.EP)

    def test_lang_placeholder_still_passes_through(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_for(self.EP, "[lang]"), "/[lang]" + self.EP
            )


class TestLangUrlPrefix(TestUrlCommon):
    def test_prefixes_a_path(self):
        self.assertEqual(self.IrHttp._lang_url_prefix("/shop", "fr"), "/fr/shop")

    def test_root_does_not_gain_a_trailing_slash(self):
        self.assertEqual(self.IrHttp._lang_url_prefix("/", "fr"), "/fr")

    def test_non_root_relative_path_is_repaired_and_logged(self):
        with self.assertLogs(
            "odoo.addons.http_routing.models.ir_http", level="WARNING"
        ):
            self.assertEqual(self.IrHttp._lang_url_prefix("shop", "fr"), "/fr/shop")

    def test_query_string_is_left_alone(self):
        self.assertEqual(
            self.IrHttp._lang_url_prefix("/shop?a=b", "fr"), "/fr/shop?a=b"
        )


class TestLangUrlUnprefix(TestUrlCommon):
    def test_split_reports_the_code_and_the_rest(self):
        with MockRequest(self.env, mock_router=False):
            self.assertEqual(self.IrHttp._lang_url_split("/fr/shop"), ("fr", "/shop"))
            self.assertEqual(self.IrHttp._lang_url_split("/fr"), ("fr", "/"))
            self.assertEqual(self.IrHttp._lang_url_split("/shop"), (None, "/shop"))

    def test_only_url_codes_count_not_full_codes(self):
        with MockRequest(self.env, mock_router=False):
            self.assertEqual(
                self.IrHttp._lang_url_split("/fr_FR/shop"), (None, "/fr_FR/shop")
            )

    def test_frontend_url_codes_is_the_single_source(self):
        with MockRequest(self.env, mock_router=False):
            codes = self.env["ir.http"]._frontend_url_codes()
        self.assertIn("fr", codes)
        self.assertIn("en", codes)
        self.assertEqual(
            sorted(codes),
            sorted(lg.url_code for lg in self.env["res.lang"]._get_frontend().values()),
        )

    def test_strips_a_known_url_code(self):
        with MockRequest(self.env, mock_router=False):
            self.assertEqual(self.IrHttp._lang_url_unprefix("/fr/shop"), "/shop")
            self.assertEqual(self.IrHttp._lang_url_unprefix("/en/shop"), "/shop")

    def test_bare_prefix_becomes_root(self):
        with MockRequest(self.env, mock_router=False):
            for path in ("/fr", "/fr/"):
                self.assertEqual(self.IrHttp._lang_url_unprefix(path), "/")

    def test_explicit_url_codes_need_no_request(self):
        codes = self.env["ir.http"]._frontend_url_codes()
        self.assertEqual(
            self.IrHttp._lang_url_split("/fr/shop", codes), ("fr", "/shop")
        )
        self.assertEqual(self.IrHttp._lang_url_unprefix("/fr/shop", codes), "/shop")
        self.assertEqual(self.IrHttp._lang_url_split("/shop", codes), (None, "/shop"))
        self.assertEqual(
            self.IrHttp._lang_url_split("/fr/shop", ["en"]), (None, "/fr/shop")
        )

    def test_unprefixed_path_untouched(self):
        with MockRequest(self.env, mock_router=False):
            for path in ("/shop", "/", "", "/frites/x", "/fr_FR/shop"):
                self.assertEqual(self.IrHttp._lang_url_unprefix(path), path)

    def test_round_trips_with_prefix(self):
        with MockRequest(self.env, mock_router=False):
            for path in ("/shop", "/"):
                prefixed = self.IrHttp._lang_url_prefix(path, "fr")
                self.assertEqual(self.IrHttp._lang_url_unprefix(prefixed), path)


class TestUrlSplitSuffix(TestUrlCommon):
    def test_splits_query_and_fragment(self):
        cases = [
            ("/shop", ("/shop", "")),
            ("/shop?a=b", ("/shop", "?a=b")),
            ("/shop#top", ("/shop", "#top")),
            ("/shop?a=b#top", ("/shop", "?a=b#top")),
            ("/shop#top?a=b", ("/shop", "#top?a=b")),
            ("/shop#a#b", ("/shop", "#a#b")),
            ("", ("", "")),
            ("#top", ("", "#top")),
            ("?a=b", ("", "?a=b")),
        ]
        for url, expected in cases:
            with self.subTest(url=url):
                self.assertEqual(self.IrHttp._url_split_suffix(url), expected)

    def test_is_lossless(self):
        for url in ("/a/b-1?x=1&x=2#f?g", "/", "", "#", "?", "/a#", "/a?"):
            with self.subTest(url=url):
                path, suffix = self.IrHttp._url_split_suffix(url)
                self.assertEqual(path + suffix, url)


class TestIsMultilangUrl(TestUrlCommon):
    def setUp(self):
        super().setUp()
        self.addCleanup(self.registry.clear_cache, "routing")

    def test_multilang_route(self):
        with MockRequest(self.env, mock_router=False):
            self.assertTrue(self.IrHttp._is_multilang_url(self.EP))

    def test_lang_prefix_is_ignored_for_matching(self):
        with MockRequest(self.env, mock_router=False):
            self.assertTrue(self.IrHttp._is_multilang_url("/fr" + self.EP))

    def test_unrouted_path_is_multilang(self):
        with MockRequest(self.env, mock_router=False):
            self.assertTrue(self.IrHttp._is_multilang_url("/no/such/page"))

    def test_static_and_web_are_not_multilang(self):
        with MockRequest(self.env, mock_router=False):
            self.assertFalse(self.IrHttp._is_multilang_url("/web/login"))
            self.assertFalse(self.IrHttp._is_multilang_url("/foo/static/x.js"))

    def test_query_and_fragment_do_not_hide_the_lang_prefix(self):
        with MockRequest(self.env, mock_router=False):
            for suffix in ("", "?a=b", "#top", "?a=b#top", "#top?a=b"):
                with self.subTest(suffix=suffix):
                    self.assertEqual(
                        self.IrHttp._is_multilang_url("/fr" + self.EP + suffix),
                        self.IrHttp._is_multilang_url(self.EP),
                    )
                    self.assertEqual(
                        self.IrHttp._is_multilang_url("/fr" + suffix),
                        self.IrHttp._is_multilang_url("/"),
                    )

    def test_static_and_web_still_detected_behind_a_lang_prefix(self):
        with MockRequest(self.env, mock_router=False):
            self.assertFalse(self.IrHttp._is_multilang_url("/fr/web/login"))
            self.assertFalse(self.IrHttp._is_multilang_url("/fr/foo/static/x.js?v=1"))


class TestUrlLocalized(TestUrlCommon):
    def test_happy_path_prefixes_lang(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_localized(self.EP, lang_code="fr_FR"),
                "/fr" + self.EP,
            )

    def test_default_lang_no_prefix(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_localized(self.EP, lang_code="en_US"), self.EP
            )

    def test_force_default_lang_prefixes_anyway(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_localized(
                    self.EP, lang_code="en_US", force_default_lang=True
                ),
                "/en" + self.EP,
            )

    def test_canonical_domain_joined_and_query_dropped(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_localized(
                    self.EP + "?a=b",
                    lang_code="fr_FR",
                    canonical_domain="https://example.com",
                ),
                "https://example.com/fr" + self.EP,
            )

    def test_query_string_preserved(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_localized(self.EP + "?a=b", lang_code="fr_FR"),
                "/fr" + self.EP + "?a=b",
            )

    def test_fragment_is_preserved_not_quoted(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_localized(self.EP + "#top", lang_code="fr_FR"),
                "/fr" + self.EP + "#top",
            )
            self.assertEqual(
                self.IrHttp._url_localized(self.EP + "?a=b#top", lang_code="fr_FR"),
                "/fr" + self.EP + "?a=b#top",
            )
            self.assertEqual(
                self.IrHttp._url_localized(self.EP + "#top?a=b", lang_code="fr_FR"),
                "/fr" + self.EP + "#top?a=b",
            )

    def test_canonical_domain_drops_query_and_fragment(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_localized(
                    self.EP + "?a=b#top",
                    lang_code="fr_FR",
                    canonical_domain="https://example.com",
                ),
                "https://example.com/fr" + self.EP,
            )

    def test_existing_lang_prefix_is_replaced_not_stacked(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_localized("/fr" + self.EP, lang_code="fr_FR"),
                "/fr" + self.EP,
            )
            self.assertEqual(
                self.IrHttp._url_localized("/en" + self.EP, lang_code="fr_FR"),
                "/fr" + self.EP,
            )
            self.assertEqual(
                self.IrHttp._url_localized("/fr" + self.EP, lang_code="en_US"),
                self.EP,
            )
            self.assertEqual(
                self.IrHttp._url_localized("/fr/no/such/page-4", lang_code="fr_FR"),
                "/fr/no/such/page-4",
            )

    def test_unknown_lang_falls_back_to_request_lang(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_localized(self.EP, lang_code="xx_XX"), self.EP
            )

    def test_unmatched_url_degrades(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_localized("/no/such/page-4", lang_code="fr_FR"),
                "/fr/no/such/page-4",
            )

    def test_unmatched_url_quoting(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_localized("/no/such/caf%C3%A9-4", lang_code="fr_FR"),
                "/fr/no/such/caf%C3%A9-4",
            )
            self.assertEqual(
                self.IrHttp._url_localized("/no such/page-4", lang_code="fr_FR"),
                "/fr/no%20such/page-4",
            )

    def test_dot_segments_degrade_instead_of_raising(self):
        """A scanner probing with '..' must not break the page being rendered."""
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            for url in (
                "/no/such/../../etc/passwd",
                "/no/such/%2e%2e/page-4",
                "/no/such/./page-4",
            ):
                with self.subTest(url=url):
                    self.assertEqual(
                        self.IrHttp._url_localized(
                            url,
                            lang_code="fr_FR",
                            canonical_domain="https://example.com",
                        ),
                        "/fr" + url,
                        "a dot-segment path is never canonical: it degrades to"
                        " the root-relative path instead of being domain-joined",
                    )

    def test_non_local_urls_untouched(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            for url in (
                "https://odoo.com" + self.EP,
                "//cdn.example.com/x.png",
                "mailto:a@b.c",
                "tel:+3215",
                "#anchor",
                "relative/path-1",
            ):
                self.assertEqual(
                    self.IrHttp._url_localized(url, lang_code="fr_FR"), url
                )

    def test_non_local_url_ignores_canonical_domain(self):
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_localized(
                    "https://odoo.com" + self.EP,
                    lang_code="fr_FR",
                    canonical_domain="https://example.com",
                ),
                "https://odoo.com" + self.EP,
            )

    def test_empty_url_still_falls_back_to_request_path(self):
        with MockRequest(
            self.env, path=self.EP, context={"lang": "en_US"}, mock_router=False
        ):
            self.assertEqual(
                self.IrHttp._url_localized("", lang_code="fr_FR"), "/fr" + self.EP
            )
            self.assertEqual(
                self.IrHttp._url_localized(lang_code="fr_FR"), "/fr" + self.EP
            )

    def test_does_not_steer_the_live_request(self):
        with MockRequest(
            self.env,
            path="/fr" + self.EP,
            context={"lang": "en_US"},
            mock_router=False,
            is_frontend=None,
        ) as req:
            req.reroute = Mock(side_effect=AssertionError("rerouted the request"))
            before = req.httprequest.path

            self.IrHttp._url_localized("/fr" + self.EP, lang_code="fr_FR")
            self.IrHttp._url_localized(self.EP, lang_code="fr_FR")
            self.IrHttp._url_localized("/no/such/page-4", lang_code="fr_FR")

            req.reroute.assert_not_called()
            self.assertEqual(req.httprequest.path, before)
            self.assertFalse(
                hasattr(req, "is_frontend"),
                "generating a URL must not flag the request as routed",
            )

    def test_request_redirect_degrades(self):
        self.patch(
            self.registry["ir.http"],
            "_match",
            Mock(side_effect=werkzeug.routing.RequestRedirect("http://x/moved")),
        )
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_localized(self.EP, lang_code="fr_FR"),
                "/fr" + self.EP,
            )

    def test_method_not_allowed_degrades(self):
        self.patch(
            self.registry["ir.http"],
            "_match",
            Mock(side_effect=werkzeug.exceptions.MethodNotAllowed()),
        )
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_localized(self.EP, lang_code="fr_FR"),
                "/fr" + self.EP,
            )


class TestDefaultLang(TestUrlCommon):
    def test_stale_default_falls_back_to_an_active_lang(self):
        self.env["ir.default"].set("res.partner", "lang", "xx_XX")
        with MockRequest(self.env, context={"lang": "fr_FR"}, mock_router=False):
            default = self.IrHttp._get_default_lang()
            self.assertTrue(default, "must not return the falsy dummy LangData")
            self.assertIn(default.code, self.env["res.lang"]._get_frontend())
            self.assertTrue(default.url_code)

    def test_stale_default_does_not_invert_canonical_urls(self):
        self.env["ir.default"].set("res.partner", "lang", "xx_XX")
        with MockRequest(self.env, context={"lang": "en_US"}, mock_router=False):
            self.assertEqual(
                self.IrHttp._url_localized(self.EP, lang_code="en_US"), self.EP
            )
            self.assertEqual(self.IrHttp._url_for(self.EP), self.EP)
            self.assertEqual(
                self.IrHttp._url_localized(self.EP, lang_code="fr_FR"),
                "/fr" + self.EP,
            )

    def test_default_lang_is_not_queried_per_call(self):
        with MockRequest(self.env, context={"lang": "fr_FR"}, mock_router=False):
            self.IrHttp._get_default_lang()
            self.env.flush_all()
            before = self.cr.sql_statement_count
            for _ in range(10):
                self.IrHttp._get_default_lang()
            self.assertEqual(self.cr.sql_statement_count - before, 0)

    def test_default_lang_cache_is_invalidated(self):
        self.assertEqual(self.IrHttp._get_default_lang_code(), "en_US")
        self.env["ir.default"].set("res.partner", "lang", "fr_FR")
        self.assertEqual(
            self.IrHttp._get_default_lang_code(),
            "fr_FR",
            "ir.default writes must drop the ormcache (they clear_cache())",
        )
        self.env["res.lang"]._activate_lang("nl_NL")
        self.assertEqual(
            self.IrHttp._get_default_lang_code(),
            "fr_FR",
            "res.lang writes clear_cache('stable'), which cascades to 'default'",
        )


class TestUrlRewrite(TestUrlCommon):
    def setUp(self):
        super().setUp()
        self.addCleanup(self.registry.clear_cache, "routing")

    def test_method_not_allowed_reports_unrouted(self):
        router = MagicMock()
        router.return_value.bind.return_value.match.side_effect = (
            werkzeug.exceptions.MethodNotAllowed()
        )
        with (
            MockRequest(self.env, mock_router=False),
            patch("odoo.http.root.get_routing_map", router),
        ):
            self.assertEqual(
                self.env["ir.http"].url_rewrite("/put/only"), ("/put/only", False)
            )

    def test_works_without_a_request(self):
        self.assertEqual(
            self.env["ir.http"].url_rewrite(self.EP)[0],
            self.EP,
        )

    def test_redirect_loop_degrades(self):
        targets = {"/loop/a": "/loop/b", "/loop/b": "/loop/a"}

        def fake_match(path, method=None):
            raise werkzeug.routing.RequestRedirect("http://x" + targets[path])

        router = MagicMock()
        router.return_value.bind.return_value.match.side_effect = fake_match
        with (
            MockRequest(self.env, mock_router=False),
            patch("odoo.http.root.get_routing_map", router),
            self.assertLogs(
                "odoo.addons.http_routing.models.ir_http", level="WARNING"
            ) as capture,
        ):
            path, func = self.env["ir.http"].url_rewrite("/loop/a")
        self.assertEqual(path, "/loop/b")
        self.assertFalse(func)
        self.assertIn("Redirect loop", capture.output[0])

    def test_redirect_loop_does_not_poison_sibling_cache(self):
        targets = {"/loop/a": "/loop/b", "/loop/b": "/loop/a"}

        def fake_match(path, method=None):
            raise werkzeug.routing.RequestRedirect("http://x" + targets[path])

        router = MagicMock()
        router.return_value.bind.return_value.match.side_effect = fake_match
        with (
            MockRequest(self.env, mock_router=False),
            patch("odoo.http.root.get_routing_map", router),
            self.assertLogs("odoo.addons.http_routing.models.ir_http", level="WARNING"),
        ):
            path_a, func_a = self.env["ir.http"].url_rewrite("/loop/a")
            path_b, func_b = self.env["ir.http"].url_rewrite("/loop/b")
        self.assertEqual(path_a, "/loop/b")
        self.assertFalse(func_a)
        self.assertEqual(path_b, "/loop/a")
        self.assertFalse(func_b)


class TestIsMultilangUrlWithoutRequest(TestUrlCommon):
    def setUp(self):
        super().setUp()
        self.addCleanup(self.registry.clear_cache, "routing")

    def test_works_without_a_request(self):
        self.assertTrue(self.IrHttp._is_multilang_url(self.EP))
        self.assertFalse(self.IrHttp._is_multilang_url("/web/login"))
        self.assertFalse(self.IrHttp._is_multilang_url("/foo/static/x.js"))

    def test_lang_prefix_still_ignored_without_a_request(self):
        self.assertTrue(self.IrHttp._is_multilang_url("/fr" + self.EP))
