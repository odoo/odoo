import json
from unittest.mock import Mock, patch
from urllib.parse import urlencode

from odoo import tests
from odoo.libs.guarded_http import GuardedSession
from odoo.tools.misc import mute_logger, submap

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website.controllers.main import Website


@tests.tagged("post_install", "-at_install")
class TestControllers(tests.HttpCase):
    @mute_logger("odoo.addons.http_routing.models.ir_http", "odoo.http")
    def test_last_created_pages_autocompletion(self):
        self.authenticate("admin", "admin")
        Page = self.env["website.page"]
        last_5_url_edited = []
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        suggested_links_url = base_url + "/website/get_suggested_links"

        old_pages = Page
        for i in range(10):
            new_page = Page.create(
                {
                    "name": "Generic",
                    "type": "qweb",
                    "arch": """
                    <div>content</div>
                """,
                    "key": "test.generic_view-%d" % i,
                    "url": "/generic-%d" % i,
                    "is_published": True,
                }
            )
            if i % 2 == 0:
                old_pages += new_page
            else:
                last_5_url_edited.append(new_page.url)

        self.url_open(
            url=suggested_links_url, json={"params": {"needle": "/", "limit": 10}}
        )
        old_pages._write_multi([{"write_date": "2020-01-01"}] * len(old_pages))

        res = self.url_open(
            url=suggested_links_url, json={"params": {"needle": "/", "limit": 10}}
        )
        resp = json.loads(res.content)
        assert "result" in resp
        suggested_links = resp["result"]
        last_modified_history = next(
            o for o in suggested_links["others"] if o["title"] == "Last modified pages"
        )
        last_modified_values = (o["value"] for o in last_modified_history["values"])

        matching_pages = {o["value"] for o in suggested_links["matching_pages"]}
        self.assertEqual(
            set(last_modified_values), set(last_5_url_edited) - matching_pages
        )

    def test_02_client_action_iframe_url(self):
        urls = [
            "/",
            "/contactus",
            "/website/info",
            "/contactus?name=testing",
        ]
        for url in urls:
            resp = self.url_open(f"/@{url}")
            self.assertURLEqual(
                resp.url, url, "Public user should have landed in the frontend"
            )
        self.authenticate("admin", "admin")
        for url in urls:
            resp = self.url_open(f"/@{url}")
            backend_params = urlencode({"path": url})
            self.assertURLEqual(
                resp.url,
                f"/odoo/action-website.website_preview?{backend_params}",
                "Internal user should have landed in the backend",
            )

    def test_03_website_image(self):
        attachment = self.env["ir.attachment"].create(
            {
                "name": "one_pixel.png",
                "datas": "iVBORw0KGgoAAAANSUhEUgAAAAYAAAAGCAYAAADgzO9IAAAAJElEQVQI"
                "mWP4/b/qPzbM8Pt/1X8GBgaEAJTNgFcHXqOQMV4dAMmObXXo1/BqAAAA"
                "AElFTkSuQmCC",
                "public": True,
            }
        )

        res = self.url_open(
            f"/website/image/ir.attachment/{attachment.id}_unique/raw?download=1"
        )
        res.raise_for_status()

        headers = {
            "Content-Length": "93",
            "Content-Type": "image/png",
            "Content-Disposition": "attachment; filename=one_pixel.png",
            "Cache-Control": "public, max-age=31536000, immutable",
        }
        self.assertEqual(submap(res.headers, headers.keys()), headers)
        self.assertEqual(res.content, attachment.raw)

    def test_04_website_partner_avatar(self):
        partner = self.env["res.partner"].create({"name": "Jack O'Neill"})

        with self.subTest(published=False):
            partner.website_published = False
            res = self.url_open(
                f"/website/image/res.partner/{partner.id}/avatar_128?download=1"
            )
            self.assertEqual(
                res.status_code,
                404,
                "Public user should't access avatar of unpublished partners",
            )

        with self.subTest(published=True):
            partner.website_published = True
            res = self.url_open(
                f"/website/image/res.partner/{partner.id}/avatar_128?download=1"
            )
            self.assertEqual(
                res.status_code,
                200,
                "Public user should access avatar of published partners",
            )

        with self.subTest(published=True):
            partner.website_published = True
            self.patch(
                self.env.registry[partner._name].avatar_128,
                "groups",
                "base.group_system",
            )
            res = self.url_open(
                f"/website/image/res.partner/{partner.id}/avatar_128?download=1"
            )
            self.assertEqual(
                res.status_code,
                404,
                "Public user shouldn't access record fields with a `groups` even if published",
            )

    @patch.object(GuardedSession, "request")
    def test_05_seo_suggest_language_regex(self, mock_get):
        mock_response = Mock()
        mock_response.content = """<?xml version="1.0"?>
        <toplevel>
            <CompleteSuggestion>
                <suggestion data="test suggestion"/>
            </CompleteSuggestion>
        </toplevel>"""
        mock_get.return_value = mock_response

        test_cases = [
            ("en_US", ["en", "US"]),
            ("fr_FR", ["fr", "FR"]),
            ("es", ["es", ""]),
            ("sr_RS@latin", ["sr", "RS"]),
            ("zh_CN@pinyin", ["zh", "CN"]),
            ("sr@latin", ["sr", ""]),
            ("", ["en", "US"]),
        ]

        for lang_input, expected_output in test_cases:
            with self.subTest(lang=lang_input):
                with MockRequest(self.env):
                    result = Website.seo_suggest(self, keywords="test", lang=lang_input)

                called_params = mock_get.call_args[1]["params"]

                self.assertEqual(called_params["hl"], expected_output[0])

                self.assertEqual(called_params["gl"], expected_output[1])

                self.assertIn("test suggestion", result)

    def test_06_website_action(self):
        self.authenticate("admin", "admin")
        self.env["ir.actions.server"].create(
            {
                "name": "Test Action",
                "website_published": True,
                "website_path": "my_test_action",
                "model_id": self.ref("base.model_res_partner"),
                "code": """response = request.prepare_response("{'message': 'Succeeded'}")""",
                "state": "code",
                "type": "ir.actions.server",
            }
        )

        res = self.url_open("/website/action/my_test_action")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "{'message': 'Succeeded'}")

        res = self.url_open("/website/action/foo.does_not_exist", allow_redirects=False)
        self.assertNotEqual(res.status_code, 500)
        self.assertIn(res.status_code, (301, 302, 303))

        res = self.url_open("/website/action/base.user_root", allow_redirects=False)
        self.assertNotEqual(res.status_code, 500)
        self.assertIn(res.status_code, (301, 302, 303))

    def test_08_check_can_modify_any_empty(self):
        self.authenticate("admin", "admin")
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        res = self.url_open(
            base_url + "/website/check_can_modify_any",
            json={"params": {"records": []}},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["result"], True)

    def test_09_autocomplete_invalid_order_no_error(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        res = self.url_open(
            base_url + "/website/snippet/autocomplete",
            json={
                "params": {
                    "search_type": "pages",
                    "term": "a",
                    "order": "nonexistent_field desc",
                    "options": {"displayDescription": True},
                }
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("error", res.json())
        self.assertIn("result", res.json())

    def test_07_get_alt_images(self):
        test_view = self.env["ir.ui.view"].create(
            {
                "name": "Image Template Test View",
                "type": "qweb",
                "arch_db": """
                <template>
                    <div>
                        <img t-att-src="dynamic_source1" />
                        <img t-att-src="dynamic_source2" alt="Dynamic img" />
                        <img t-attf-src="/path/{{variable}}" />
                        <img src="/static/image1.jpg" alt="Static 1" />
                        <img src="/static/image2.jpg" alt="Static 2" role="presentation" />
                        <img src="/static/image3.png" />
                        <img src="/static/image4.png" role="presentation" />
                    </div>
                </template>
            """,
            }
        )
        models = [{"model": "ir.ui.view", "id": test_view.id, "field": "arch"}]

        with MockRequest(self.env, website=self.env.ref("website.default_website")):
            result = Website().get_alt_images(models)
            parsed_result = json.loads(result)

            expected_srcs = [
                "/static/image1.jpg",
                "/static/image3.png",
                "/static/image4.png",
            ]
            actual_srcs = [img["src"] for img in parsed_result]

            self.assertEqual(
                expected_srcs,
                actual_srcs,
                "XPath should filter out dynamic images, include only static",
            )


@tests.tagged("post_install", "-at_install")
class TestAutocompleteInputBounds(tests.HttpCase):
    """`/website/snippet/autocomplete` is open to anyone, so its numbers are clamped.

    `limit` was clamped and `max_nb_chars` was not, although the latter reaches
    `textwrap.shorten`, which refuses a width smaller than its placeholder. A
    visitor could turn a search box into a 500 with a JSON field.
    """

    def setUp(self):
        super().setUp()
        self.url = (
            self.env["ir.config_parameter"].sudo().get_param("web.base.url")
            + "/website/snippet/autocomplete"
        )
        self.env["website.page"].create(
            {
                "name": "Autocomplete Bound",
                "type": "qweb",
                "key": "website.autocomplete_bound",
                "url": "/autocomplete-bound",
                "is_published": True,
                "arch": '<t t-name="website.autocomplete_bound">'
                "<div>autocompleteboundbody</div></t>",
            }
        )
        self.env.flush_all()

    def _call(self, **params):
        params.setdefault("search_type", "pages")
        params.setdefault("term", "autocompleteboundbody")
        params.setdefault("options", {"displayDescription": True})
        return self.url_open(self.url, json={"params": params}).json()

    def test_a_narrow_width_does_not_raise(self):
        for max_nb_chars in (0, 1, -5):
            with self.subTest(max_nb_chars=max_nb_chars):
                payload = self._call(max_nb_chars=max_nb_chars)
                self.assertNotIn("error", payload)
                self.assertIn("result", payload)

    def test_a_result_count_never_promises_rows_the_payload_omits(self):
        for limit in (0, None, []):
            with self.subTest(limit=limit):
                payload = self._call(limit=limit)["result"]
                self.assertEqual(
                    bool(payload["results"]),
                    bool(payload["results_count"]),
                    "a non-zero count with no rows makes the widget claim results "
                    "it never renders",
                )

    def test_a_wide_width_is_still_honoured(self):
        payload = self._call(max_nb_chars=999)["result"]
        self.assertTrue(payload["results"])
        self.assertNotIn("...", payload["results"][0]["name"])
