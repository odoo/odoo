import base64
import copy
import json
import logging
import struct
import zipfile
from io import BytesIO
from unittest.mock import Mock, patch

from lxml import html
from werkzeug.exceptions import Forbidden, NotFound

from odoo import Command
from odoo.exceptions import AccessDenied, UserError
from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website.controllers import theme as website_theme
from odoo.addons.website.controllers.form import WebsiteForm
from odoo.addons.website.controllers.main import Website
from odoo.addons.website.controllers.model_page import ModelPageController

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestControllerIntegrity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("website.default_website")
        cls.view = cls.env["ir.ui.view"].create(
            {
                "name": "Controller integrity",
                "type": "qweb",
                "key": "website.test_controller_integrity",
                "arch": '<div><img t-att-src="source"/><img src="/first"/>'
                '<img src="/second"/><a href="/old">Link</a></div>',
            }
        )

    def test_image_edits_use_the_ids_returned_by_the_reader(self):
        models = [{"model": "ir.ui.view", "id": self.view.id, "field": "arch"}]
        original_models = copy.deepcopy(models)
        with MockRequest(self.env, website=self.website):
            controller = Website()
            images = json.loads(controller.get_alt_images(models))
            images[0]["alt"] = 'First & "only"'
            images[1]["decorative"] = True
            original_images = copy.deepcopy(images)
            with patch.object(
                type(self.view),
                "write",
                autospec=True,
                side_effect=type(self.view).write,
            ) as write:
                controller.update_alt_images(images)
            writes = [
                call for call in write.call_args_list if call.args[0] == self.view
            ]

        tree = html.fromstring(self.view.arch)
        _logger.debug("Image edit result: %s; writes=%d", self.view.arch, len(writes))
        self.assertIsNone(tree.xpath("//img[@t-att-src]")[0].get("alt"))
        self.assertEqual(
            tree.xpath('//img[@src="/first"]')[0].get("alt"), 'First & "only"'
        )
        self.assertEqual(
            tree.xpath('//img[@src="/second"]')[0].get("role"), "presentation"
        )
        self.assertEqual(len(writes), 1)
        self.assertEqual(models, original_models)
        self.assertEqual(images, original_images)

    def test_font_upload_limits_are_checked_before_creating_attachments(self):
        def archive(entries):
            buffer = BytesIO()
            with zipfile.ZipFile(
                buffer, "w", compression=zipfile.ZIP_DEFLATED
            ) as fonts:
                for name, content in entries:
                    fonts.writestr(name, content)
            return base64.b64encode(buffer.getvalue()).decode()

        cases = [
            ("invalid.woff", "not base64!"),
            ("large.woff", base64.b64encode(b"wOFF" + b"x" * 61).decode()),
            (
                "family.zip",
                archive([("ok.woff", b"wOFF"), ("large.woff", b"wOFF" + b"x" * 61)]),
            ),
            (
                "family.zip",
                archive(
                    [("a.woff", b"wOFF" + b"x" * 60), ("b.woff", b"wOFF" + b"x" * 60)]
                ),
            ),
            ("family.zip", archive([(f"{i}.woff", b"wOFF") for i in range(4)])),
        ]
        for name, data in cases:
            with (
                self.subTest(name=name, encoded_size=len(data)),
                MockRequest(self.env, website=self.website),
                patch.object(website_theme, "MAX_FONT_FILE_SIZE", 64),
                # No `create=True`: it would make a patch aimed at the wrong
                # module look like it worked, which is how these limits moving
                # to controllers/theme.py stayed invisible in two of the three
                # font tests until the others errored.
                patch.object(website_theme, "MAX_FONT_ARCHIVE_SIZE", 100),
                patch.object(website_theme, "MAX_FONT_ARCHIVE_ENTRIES", 3),
                patch.object(
                    type(self.env["ir.attachment"]),
                    "create",
                    wraps=self.env["ir.attachment"].create,
                ) as create,
            ):
                _logger.debug(
                    "Rejecting font fixture %s encoded_size=%d", name, len(data)
                )
                with self.assertRaises(UserError):
                    Website().theme_upload_font(name, data)
                create.assert_not_called()

    def test_font_upload_accepts_standalone_and_archive(self):
        content = b"wOFF" + b"x" * 60
        archive = BytesIO()
        with zipfile.ZipFile(archive, "w") as fonts:
            fonts.writestr("nested/example.woff", content)
        with (
            MockRequest(self.env, website=self.website),
            patch.object(website_theme, "MAX_FONT_FILE_SIZE", len(content)),
        ):
            for name, payload in [
                ("example.woff", content),
                ("family.zip", archive.getvalue()),
            ]:
                uploaded = Website().theme_upload_font(
                    name, base64.b64encode(payload).decode()
                )
                self.assertEqual(len(uploaded), 1)
                attachment = self.env["ir.attachment"].browse(uploaded[0]["id"])
                self.assertEqual(attachment.raw, content)
                self.assertEqual(attachment.mimetype, "font/woff")

    def test_font_upload_rejects_encoded_oversize_before_decoding(self):
        with (
            MockRequest(self.env, website=self.website),
            patch.object(website_theme, "MAX_FONT_UPLOAD_SIZE", 3),
            patch.object(
                website_theme.base64, "b64decode", wraps=base64.b64decode
            ) as decode,
        ):
            with self.assertRaises(UserError):
                Website().theme_upload_font("large.woff", "eHh4eA==")
            decode.assert_not_called()
            _logger.debug("Oversized base64 font rejected without decoding")

    def test_font_archive_errors_are_user_errors(self):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("example.woff", b"wOFFcontent")
        original = buffer.getvalue()
        central = original.index(b"PK\x01\x02")
        for failure in ("encrypted", "unsupported", "checksum", "directory", "deflate"):
            payload = bytearray(original)
            if failure == "encrypted":
                struct.pack_into("<H", payload, 6, 1)
                struct.pack_into("<H", payload, central + 8, 1)
            elif failure == "unsupported":
                struct.pack_into("<H", payload, 8, 99)
                struct.pack_into("<H", payload, central + 10, 99)
            elif failure == "checksum":
                payload[payload.index(b"wOFFcontent") + 4] ^= 1
            elif failure == "directory":
                payload[central : central + 4] = b"BAD!"
            else:
                compressed = BytesIO()
                with zipfile.ZipFile(
                    compressed, "w", compression=zipfile.ZIP_DEFLATED
                ) as archive:
                    archive.writestr("example.woff", b"wOFFcontent")
                payload = bytearray(compressed.getvalue())
                payload[30 + len("example.woff")] = 7
            with (
                self.subTest(failure=failure),
                MockRequest(self.env, website=self.website),
            ):
                _logger.debug("Testing font ZIP failure=%s", failure)
                with self.assertRaises(UserError):
                    Website().theme_upload_font(
                        "family.zip", base64.b64encode(payload).decode()
                    )

    def test_seo_empty_html_is_a_noop(self):
        partner = self.env["res.partner"].create(
            {"name": "Empty SEO", "comment": "   "}
        )
        before = partner.comment
        with MockRequest(self.env, website=self.website):
            controller = Website()
            self.assertEqual(
                json.loads(
                    controller.get_alt_images(
                        [{"model": partner._name, "id": partner.id, "field": "comment"}]
                    )
                ),
                [],
            )
            controller.update_broken_links(
                [
                    {
                        "res_model": partner._name,
                        "res_id": partner.id,
                        "field": "comment",
                        "oldLink": "/old",
                        "newLink": "/new",
                        "remove": False,
                    }
                ]
            )
        _logger.debug("Empty HTML before=%r after=%r", before, partner.comment)
        self.assertEqual(partner.comment, before)

    def test_link_updates_are_batched_without_changing_sequential_semantics(self):
        links = [
            {
                "res_model": "ir.ui.view",
                "res_id": self.view.id,
                "field": "arch",
                "oldLink": old,
                "newLink": new,
                "remove": False,
            }
            for old, new in [("/old", "/middle"), ("/middle", "/new?a=1&b=2")]
        ]
        original = copy.deepcopy(links)
        with MockRequest(self.env, website=self.website):
            with patch.object(
                type(self.view),
                "write",
                autospec=True,
                side_effect=type(self.view).write,
            ) as write:
                Website().update_broken_links(links)
        writes = [call for call in write.call_args_list if call.args[0] == self.view]
        self.assertEqual(
            html.fromstring(self.view.arch).xpath("//a")[0].get("href"), "/new?a=1&b=2"
        )
        self.assertEqual(len(writes), 1)
        self.assertEqual(links, original)

    def test_unknown_image_id_does_not_write(self):
        before = self.view.arch
        with MockRequest(self.env, website=self.website):
            Website().update_alt_images(
                [
                    {
                        "res_model": "ir.ui.view",
                        "res_id": self.view.id,
                        "field": "arch",
                        "id": "unknown",
                        "decorative": False,
                        "alt": "wrong",
                    }
                ]
            )
        self.assertEqual(self.view.arch, before)

    def test_stale_image_position_cannot_edit_a_different_source(self):
        with MockRequest(self.env, website=self.website):
            controller = Website()
            images = json.loads(
                controller.get_alt_images(
                    [{"model": self.view._name, "id": self.view.id, "field": "arch"}]
                )
            )
            images[0]["alt"] = "Description of the original first image"
            self.view.arch = '<div><img src="/inserted"/><img src="/first"/><img src="/second"/></div>'
            before = self.view.arch
            _logger.debug(
                "Stale image fixture id=%s expected_src=%s",
                images[0]["id"],
                images[0]["src"],
            )
            with self.assertRaises(UserError):
                controller.update_alt_images(images[:1])
        self.assertEqual(self.view.arch, before)

    def test_deleted_image_target_is_not_silently_ignored(self):
        with MockRequest(self.env, website=self.website):
            controller = Website()
            images = json.loads(
                controller.get_alt_images(
                    [{"model": self.view._name, "id": self.view.id, "field": "arch"}]
                )
            )
            images[-1]["alt"] = "Description of the deleted image"
            self.view.arch = '<div><img src="/first"/></div>'
            before = self.view.arch
            _logger.debug("Deleted image fixture id=%s", images[-1]["id"])
            with self.assertRaises(UserError):
                controller.update_alt_images(images[-1:])
        self.assertEqual(self.view.arch, before)

    def test_emptied_html_rejects_stale_image_updates(self):
        partner = self.env["res.partner"].create(
            {"name": "Emptied image HTML", "comment": '<img src="/first"/>'}
        )
        with MockRequest(self.env, website=self.website):
            controller = Website()
            images = json.loads(
                controller.get_alt_images(
                    [{"model": partner._name, "id": partner.id, "field": "comment"}]
                )
            )
            self.assertEqual(len(images), 1)
            partner.comment = False
            images[0]["alt"] = "Stale description"
            with self.assertRaises(UserError):
                controller.update_alt_images(images)
        self.assertFalse(partner.comment)

    def test_unchanged_seo_edits_do_not_write(self):
        self.view.arch = (
            '<div><img src="/first" alt="Existing"/><a href="/old">Link</a></div>'
        )
        with MockRequest(self.env, website=self.website):
            controller = Website()
            images = json.loads(
                controller.get_alt_images(
                    [{"model": self.view._name, "id": self.view.id, "field": "arch"}]
                )
            )
            with patch.object(
                type(self.view),
                "write",
                autospec=True,
                side_effect=type(self.view).write,
            ) as write:
                controller.update_alt_images(images)
                controller.update_broken_links(
                    [
                        {
                            "res_model": self.view._name,
                            "res_id": self.view.id,
                            "field": "arch",
                            "oldLink": "/old",
                            "newLink": "/old",
                            "remove": False,
                        }
                    ]
                )
            _logger.debug("Unchanged SEO edits write calls=%d", write.call_count)
            write.assert_not_called()

    def test_public_users_cannot_edit_seo_content(self):
        before = self.view.arch
        controller = Website()
        with MockRequest(self.env(user=self.website.user_id), website=self.website):
            for endpoint in [
                controller.update_alt_images,
                controller.update_broken_links,
            ]:
                with (
                    self.subTest(endpoint=endpoint.__name__),
                    self.assertRaises(Forbidden),
                ):
                    endpoint([])
        self.assertEqual(self.view.arch, before)

    def test_invalid_mail_signature_is_rejected_before_any_processing(self):
        controller = WebsiteForm()
        self.env["ir.model"]._get("mail.mail").website_form_access = True
        with (
            MockRequest(self.env, website=self.website),
            patch.object(
                controller, "extract_data", wraps=controller.extract_data
            ) as extract,
        ):
            with self.assertRaises(AccessDenied):
                controller._handle_website_form(
                    "mail.mail",
                    email_to="recipient@example.com",
                    website_form_signature="invalid",
                )
            extract.assert_not_called()

    def test_hybrid_results_follow_the_pager_for_out_of_range_pages(self):
        """The pager decides the window and `autocomplete` renders exactly it.

        `hybrid_list` used to ask for MAX_PAGE_SEARCH_RESULTS rows and slice
        them itself, which made `len(results)` the pager's total -- a cap
        reported as a count -- and rendered every row on every page view. It now
        asks once for the counts and once for the page, so what this pins is the
        offset it asks for and the page it lands on.
        """
        page_rows = [{"name": str(i)} for i in range(50)]
        controller = Website()
        for page, expected_offset in [(0, 0), (99, 50), ("2", 50)]:
            with (
                self.subTest(page=page),
                MockRequest(self.env, website=self.website) as req,
            ):
                req.render = Mock(return_value="<rendered/>")
                calls = []

                def fake_autocomplete(*args, calls=calls, **kw):
                    # Every call answers with both counts: the controller reads
                    # them from whichever search renders the page, and a mock
                    # that only answers on one call shape pins the shape rather
                    # than the behaviour.
                    calls.append(kw)
                    return {
                        "results": page_rows,
                        "results_count": 51,
                        "results_reachable": 51,
                    }

                with patch.object(controller, "autocomplete", fake_autocomplete):
                    controller.hybrid_list(page=page, search="example")
                values = req.render.call_args.args[1]
                _logger.debug(
                    "Hybrid page=%s pager=%s calls=%s", page, values["pager"], calls
                )
                self.assertEqual(
                    calls[-1].get("offset"),
                    expected_offset,
                    "an out-of-range page must be clamped before the rows are asked for",
                )
                self.assertEqual(values["results"], page_rows)
                self.assertEqual(
                    values["search_count"], 51, "the count must be the real total"
                )
                self.assertLessEqual(
                    len(values["results"]),
                    50,
                    "a page view must not carry more than one page of rows",
                )

    def test_hybrid_reports_the_true_count_when_the_reachable_set_is_capped(self):
        controller = Website()
        with MockRequest(self.env, website=self.website) as req:
            req.render = Mock(return_value="<rendered/>")
            with patch.object(
                controller,
                "autocomplete",
                return_value={
                    "results": [],
                    "results_count": 620,
                    "results_reachable": 500,
                },
            ):
                controller.hybrid_list(page=1, search="example")
            values = req.render.call_args.args[1]
            self.assertEqual(values["search_count"], 620)
            self.assertEqual(values["search_count_reachable"], 500)
            self.assertEqual(
                values["pager"]["page_count"],
                10,
                "the pager offers only the pages it can actually serve",
            )

    def test_page_results_follow_the_pager_for_out_of_range_pages(self):
        pages = self.env["website.page"].search([], limit=2)
        self.assertEqual(len(pages), 2)
        with MockRequest(self.env, website=self.website) as req:
            req.render = Mock(return_value="<rendered/>")
            with patch.object(
                type(self.website),
                "_search_with_fuzzy",
                return_value=(2, [{"results": pages}], False),
            ):
                Website().pages_list(page=99)
            values = req.render.call_args.args[1]
        self.assertEqual(values["pages"], pages)

    def test_autocomplete_supplies_default_display_options(self):
        with MockRequest(self.env, website=self.website):
            result = Website().autocomplete(search_type="pages", term="", limit=1)
        self.assertEqual(len(result["results"]), 1)
        self.assertNotIn("description", result["parts"])

    def test_suggested_pages_are_not_repeated_when_the_name_matches(self):
        page = self.env["website.page"].search([], limit=1)
        with MockRequest(self.env, website=self.website):
            with (
                patch.object(
                    type(self.website),
                    "search_pages",
                    return_value=[{"loc": page.url, "name": page.name}],
                ),
                patch.object(
                    type(self.website), "_get_website_pages", return_value=page
                ),
            ):
                values = Website().get_suggested_link(page.name)
        self.assertEqual(values["others"][0]["values"], [])

    def test_resource_restrictions_precede_deduplication(self):
        bundles = {
            "excluded": ["shared.scss"],
            "selected": ["shared.scss", "selected.scss"],
        }
        views = [
            {
                "arch": '<t><t t-call-assets="excluded"/><t t-call-assets="selected"/><t t-call-assets="selected"/></t>'
            }
        ]
        Assets = type(self.env["website.assets"])
        with (
            MockRequest(self.env, website=self.website),
            patch.object(
                type(self.env["ir.qweb"]),
                "_get_asset_content",
                side_effect=lambda name: ([{"url": url} for url in bundles[name]], []),
            ) as content,
            patch.object(
                Assets,
                "_get_data_from_url",
                side_effect=lambda url: {
                    "module": "website",
                    "resource_path": url,
                    "customized": False,
                },
            ),
            patch.object(Assets, "_get_custom_attachment", return_value={}),
            patch.object(Assets, "_get_content_from_url", return_value="body {}"),
        ):
            result = Website()._load_resources("scss", views, ["selected"], False)
        _logger.debug(
            "Resource restriction result=%s bundle lookups=%s",
            result,
            content.call_args_list,
        )
        self.assertEqual(
            result,
            [
                [
                    "selected",
                    [
                        {
                            "url": "/website/shared.scss",
                            "arch": "body {}",
                            "customized": False,
                        },
                        {
                            "url": "/website/selected.scss",
                            "arch": "body {}",
                            "customized": False,
                        },
                    ],
                ]
            ],
        )
        content.assert_called_once_with("selected")


@tagged("post_install", "-at_install")
class TestModelPageIntegrity(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("website.default_website")
        cls.countries = cls.env["res.country"].search([], limit=3, order="id")
        cls.view = cls.env["ir.ui.view"].create(
            {
                "name": "Country directory",
                "type": "qweb",
                "arch": '<div><t t-foreach="records" t-as="record"><span t-out="record.name"/></t></div>',
                "key": "website.test_country_directory",
            }
        )
        cls.detail_view = cls.env["ir.ui.view"].create(
            {
                "name": "Country detail",
                "type": "qweb",
                "key": "website.test_country_detail",
                "arch": '<div t-out="record.name"/>',
            }
        )
        cls.page = cls.env["website.controller.page"].create(
            {
                "name": "Country directory",
                "view_id": cls.view.id,
                "record_view_id": cls.detail_view.id,
                "model_id": cls.env["ir.model"]._get_id("res.country"),
                "is_published": True,
                "record_domain": repr([("id", "in", cls.countries.ids)]),
            }
        )

    def _render(self, **kwargs):
        controller = ModelPageController()
        controller.pager_step = 2
        with MockRequest(
            self.env(user=self.website.user_id), website=self.website
        ) as req:
            req.render = Mock(return_value="<rendered/>")
            response = controller.generic_model(self.page.name_slugified, **kwargs)
            return req.render.call_args.args[1] if req.render.called else response

    def test_zero_page_uses_the_pager_offset(self):
        result = self._render(page_number=0, order="id")
        self.assertEqual(result["records"].ids, self.countries[:2].ids)
        self.assertEqual(result["pager"]["offset"], 0)

    def test_invalid_order_uses_the_default(self):
        for order in [
            "name sideways",
            "name desc,",
            "name;select",
            ",",
            "unknown desc",
        ]:
            with self.subTest(order=order):
                result = self._render(order=order)
                _logger.debug(
                    "Model page order=%r effective=%r", order, result["order_by"]
                )
                self.assertEqual(result["order_by"], "create_date desc")

    def test_valid_order_preserves_direction_and_nulls(self):
        result = self._render(order="id\tdesc nulls last")
        self.assertEqual(result["records"].ids, self.countries[-1:-3:-1].ids)

    def test_equal_sort_values_have_a_stable_pagination_tiebreaker(self):
        self.countries.write({"phone_code": 999})
        first = self._render(order="phone_code asc")
        second = self._render(order="phone_code asc", page_number=2)
        ids = first["records"].ids + second["records"].ids
        _logger.debug("Equal-sort directory pages=%s", ids)
        self.assertEqual(ids, sorted(self.countries.ids, reverse=True))
        self.assertEqual(first["order_by"], "phone_code asc")

    def test_model_without_create_date_uses_its_own_order(self):
        model = self.env["ir.module.module.dependency"]
        self.assertNotIn("create_date", model._fields)
        self.page.write(
            {
                "model_id": self.env["ir.model"]._get_id(model._name),
                "record_domain": "[]",
            }
        )
        with MockRequest(self.env, website=self.website) as req:
            req.render = Mock(return_value="<rendered/>")
            ModelPageController().generic_model(self.page.name_slugified)
            result = req.render.call_args.args[1]
        self.assertEqual(result["order_by"], model._order)
        self.assertEqual(result["records"]._name, model._name)

    def test_missing_or_excluded_record_is_not_found(self):
        for slug in [
            "missing-2147483647",
            "not-a-record",
            self.env["ir.http"]._slug(
                self.env["res.country"].search(
                    [("id", "not in", self.countries.ids)], limit=1
                )
            ),
        ]:
            with self.subTest(slug=slug), self.assertRaises(NotFound):
                self._render(record_slug=slug)

    def test_record_rules_apply_to_the_detail_page(self):
        self.env["ir.rule"].create(
            {
                "name": "Country directory restriction",
                "model_id": self.env["ir.model"]._get_id("res.country"),
                "domain_force": repr([("id", "!=", self.countries[0].id)]),
                "groups": [Command.link(self.env.ref("base.group_public").id)],
            }
        )
        slug = self.env["ir.http"]._slug(self.countries[0])
        with self.assertRaises(NotFound):
            self._render(record_slug=slug)
        base = f"/model/{self.page.name_slugified}"
        self.assertEqual(self.url_open(base + "/" + slug).status_code, 404)
        permitted_slug = self.env["ir.http"]._slug(self.countries[1])
        self.assertEqual(self.url_open(base + "/" + permitted_slug).status_code, 200)

    def test_public_http_listing_and_detail(self):
        base = f"/model/{self.page.name_slugified}"
        for suffix in ["/page/0", "?order=name+sideways", "?order=id+desc"]:
            with self.subTest(suffix=suffix):
                response = self.url_open(base + suffix)
                self.assertEqual(response.status_code, 200)
                for country in self.countries:
                    self.assertIn(country.name, response.text)
        country = self.countries[0]
        response = self.url_open(base + "/" + self.env["ir.http"]._slug(country))
        self.assertEqual(response.status_code, 200)
        self.assertIn(country.name, response.text)
        self.assertEqual(self.url_open(base + "/missing-2147483647").status_code, 404)

    def test_cold_http_record_rule_does_not_disclose_the_record(self):
        country = self.countries[0]
        name = country.name
        slug = self.env["ir.http"]._slug(country)
        self.env["ir.rule"].create(
            {
                "name": "Cold country restriction",
                "model_id": self.env["ir.model"]._get_id("res.country"),
                "domain_force": repr([("id", "!=", country.id)]),
                "groups": [Command.link(self.env.ref("base.group_public").id)],
            }
        )
        self.env.invalidate_all()

        response = self.url_open(f"/model/{self.page.name_slugified}/{slug}")

        _logger.debug(
            "Cold denied detail: status=%s contains_name=%s",
            response.status_code,
            name in response.text,
        )
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(f">{name}</div>", response.text)

    def test_excessive_model_page_redirect_preserves_search_and_order(self):
        response = self._render(
            page_number=99, order="id desc", search=self.countries[0].name
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("order=id+desc", response.headers["Location"])
        self.assertNotIn("page/99", response.headers["Location"])


@tagged("post_install", "-at_install")
class TestControllerChallenge(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("website.default_website")
        cls.other_website = cls.env["website"].create(
            {"name": "Controller challenge other"}
        )
        cls.designer = new_test_user(
            cls.env,
            login="controller_challenge_designer",
            groups="base.group_user,website.group_website_designer",
        )
        cls.view = cls.env["ir.ui.view"].create(
            {
                "name": "Controller challenge generic",
                "type": "qweb",
                "key": "website.controller_challenge_generic",
                "arch": '<div><img src="/first"/><img src="/second"/><a href="/old">link</a></div>',
            }
        )
        cls.page = cls.env["website.page"].create(
            {
                "name": "Controller challenge page",
                "view_id": cls.view.id,
                "url": "/controller-challenge",
                "is_published": True,
            }
        )

    def _specific_view(self):
        return self.env["ir.ui.view"].search(
            [
                ("key", "=", self.view.key),
                ("website_id", "=", self.website.id),
            ]
        )

    def test_seo_resolution_matches_copy_on_write_context(self):
        specific = self.view.copy(
            {
                "website_id": self.website.id,
                "key": self.view.key,
                "arch": '<div><img src="/first" alt="Specific"/><a href="/specific">link</a></div>',
            }
        )
        for no_cow, active in [(False, False), (True, True)]:
            with self.subTest(no_cow=no_cow, active=active):
                specific.active = active
                original_generic = self.view.arch
                original_specific = specific.arch
                env = self.env(
                    user=self.designer,
                    context={
                        **self.env.context,
                        "website_id": self.website.id,
                        "no_cow": no_cow,
                    },
                )
                with MockRequest(env, website=self.website, context=env.context):
                    controller = Website()
                    images = json.loads(
                        controller.get_alt_images(
                            [
                                {
                                    "model": self.view._name,
                                    "id": self.view.id,
                                    "field": "arch",
                                }
                            ]
                        )
                    )
                    images[0]["alt"] = "Updated description"
                    controller.update_alt_images(images[:1])
                target = self.view if no_cow else specific
                untouched = specific if no_cow else self.view
                _logger.debug(
                    "SEO COW context no_cow=%s active=%s target=%s arch=%s",
                    no_cow,
                    active,
                    target.id,
                    target.arch,
                )
                self.assertEqual(
                    html.fromstring(target.arch).xpath("//img/@alt"),
                    ["Updated description"],
                )
                self.assertEqual(
                    untouched.arch, original_specific if no_cow else original_generic
                )
                if not no_cow:
                    self.assertEqual(
                        html.fromstring(specific.arch).xpath("//a/@href"), ["/specific"]
                    )

    def test_batched_images_survive_copy_on_write(self):
        original = self.view.arch
        env = self.env(
            user=self.designer,
            context={**self.env.context, "website_id": self.website.id},
        )
        with MockRequest(env, website=self.website, context=env.context) as req:
            self.assertEqual(req.env.context["website_id"], self.website.id)
            controller = Website()
            images = json.loads(
                controller.get_alt_images(
                    [{"model": self.view._name, "id": self.view.id, "field": "arch"}]
                )
            )
            self.assertEqual(len(images), 2)
            for index, img in enumerate(images):
                img["alt"] = f"Description {index}"
            controller.update_alt_images(images)
        specific = self._specific_view()
        _logger.debug(
            "COW image edit: generic=%s specific=%s content=%s",
            self.view.id,
            specific.ids,
            specific.arch,
        )
        self.assertEqual(len(specific), 1)
        self.assertEqual(
            html.fromstring(specific.arch).xpath("//img/@alt"),
            ["Description 0", "Description 1"],
        )
        self.assertEqual(self.view.arch, original)
        with MockRequest(
            self.env(context={**self.env.context, "website_id": self.other_website.id}),
            website=self.other_website,
        ):
            resolved = (
                self.env["ir.ui.view"]
                .with_context(website_id=self.other_website.id)
                ._get_template_view(self.view.key)
            )
            self.assertEqual(resolved.id, self.view.id)

    def test_successive_seo_edits_keep_the_existing_website_copy(self):
        original = self.view.arch
        env = self.env(
            user=self.designer,
            context={**self.env.context, "website_id": self.website.id},
        )
        with MockRequest(env, website=self.website, context=env.context) as req:
            self.assertEqual(req.env.context["website_id"], self.website.id)
            controller = Website()
            images = json.loads(
                controller.get_alt_images(
                    [{"model": self.view._name, "id": self.view.id, "field": "arch"}]
                )
            )
            self.assertEqual(len(images), 2)
            controller.update_broken_links(
                [
                    {
                        "res_model": self.view._name,
                        "res_id": self.view.id,
                        "field": "arch",
                        "oldLink": "/old",
                        "newLink": "/new",
                        "remove": False,
                    }
                ]
            )
            images[0]["alt"] = "First description"
            controller.update_alt_images(images[:1])
            refreshed = json.loads(
                controller.get_alt_images(
                    [{"model": self.view._name, "id": self.view.id, "field": "arch"}]
                )
            )
            self.assertEqual(refreshed[0]["alt"], "First description")
        specific = self._specific_view()
        _logger.debug("Successive COW updates: %s", specific.arch)
        tree = html.fromstring(specific.arch)
        self.assertEqual(tree.xpath("//a/@href"), ["/new"])
        self.assertEqual(tree.xpath("//img[@src='/first']/@alt"), ["First description"])
        self.assertEqual(self.view.arch, original)

    def test_resource_selection_with_real_asset_records_and_file_content(self):
        path = "/website/static/src/scss/website_common.scss"
        self.env["ir.asset"].create(
            [
                {"name": bundle, "bundle": bundle, "directive": "append", "path": path}
                for bundle in [
                    "website.challenge_excluded",
                    "website.challenge_selected",
                ]
            ]
        )
        views = [
            {
                "arch": '<t><t t-call-assets="website.challenge_excluded"/><t t-call-assets="website.challenge_selected"/></t>'
            }
        ]
        env = self.env(
            user=self.designer,
            context={**self.env.context, "website_id": self.website.id},
        )
        with MockRequest(env, website=self.website, context=env.context) as req:
            self.assertEqual(req.env.context["website_id"], self.website.id)
            result = Website()._load_resources(
                "scss", views, ["website.challenge_selected"], False
            )
        _logger.debug(
            "Actual resource selection: bundles=%s urls=%s",
            [row[0] for row in result],
            [file["url"] for row in result for file in row[1]],
        )
        self.assertEqual([row[0] for row in result], ["website.challenge_selected"])
        self.assertEqual([file["url"] for row in result for file in row[1]], [path])
        self.assertGreater(len(result[0][1][0]["arch"]), 100)


@tagged("post_install", "-at_install")
class TestDynamicSnippetTemplates(HttpCase):
    """`/website/snippet/filter_templates` is public, and answers per website."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("website.default_website")
        cls.other = cls.env["website"].create({"name": "Other site"})
        View = cls.env["ir.ui.view"]
        cls.plain = View.create(
            {
                "name": "dft plain",
                "type": "qweb",
                "key": "website.dynamic_filter_template_probe_plain",
                "arch": '<t t-name="website.dynamic_filter_template_probe_plain">'
                '<section data-thumb="plain.png" data-number-of-elements="4">x</section></t>',
            }
        )
        cls.commented = View.create(
            {
                "name": "dft commented",
                "type": "qweb",
                "key": "website.dynamic_filter_template_probe_commented",
                "arch": '<t t-name="website.dynamic_filter_template_probe_commented">'
                "<!-- a perfectly ordinary leading comment -->"
                '<section data-thumb="commented.png" data-number-of-elements="6">x</section></t>',
            }
        )
        cls.foreign = View.create(
            {
                "name": "dft foreign",
                "type": "qweb",
                "website_id": cls.other.id,
                "key": "website.dynamic_filter_template_probe_foreign",
                "arch": '<t t-name="website.dynamic_filter_template_probe_foreign">'
                '<section data-thumb="foreign.png">x</section></t>',
            }
        )
        cls.env.flush_all()

    def _templates(self):
        with MockRequest(self.env, website=self.website):
            return {t["key"]: t for t in Website().get_dynamic_snippet_templates()}

    def test_a_leading_comment_does_not_erase_the_data_attributes(self):
        """lxml counts a comment as a child, so `children[0]` was the comment and
        every `data-*` came back None -- the snippet rendered with defaults and
        nothing said so."""
        templates = self._templates()
        plain = templates["website.dynamic_filter_template_probe_plain"]
        commented = templates["website.dynamic_filter_template_probe_commented"]
        self.assertEqual(plain["thumb"], "plain.png")
        self.assertEqual(plain["numOfEl"], "4")
        self.assertEqual(commented["thumb"], "commented.png")
        self.assertEqual(commented["numOfEl"], "6")

    def test_another_website_s_templates_are_not_offered(self):
        keys = self._templates()
        self.assertIn("website.dynamic_filter_template_probe_plain", keys)
        self.assertNotIn(
            "website.dynamic_filter_template_probe_foreign",
            keys,
            "a public route must not hand one site's templates to another's",
        )

    def test_a_website_still_sees_its_own_specific_template(self):
        with MockRequest(self.env, website=self.other):
            keys = {t["key"] for t in Website().get_dynamic_snippet_templates()}
        self.assertIn("website.dynamic_filter_template_probe_foreign", keys)
        self.assertIn("website.dynamic_filter_template_probe_plain", keys)

    def test_a_template_with_no_element_child_is_not_an_error(self):
        self.env["ir.ui.view"].create(
            {
                "name": "dft textonly",
                "type": "qweb",
                "key": "website.dynamic_filter_template_probe_textonly",
                "arch": '<t t-name="website.dynamic_filter_template_probe_textonly">'
                "text and nothing else</t>",
            }
        )
        self.env.flush_all()
        entry = self._templates()["website.dynamic_filter_template_probe_textonly"]
        self.assertIsNone(entry["thumb"])
