import logging
from types import SimpleNamespace
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, TransactionCase, tagged

from odoo.addons.http_routing.tests.common import MockRequest

_logger = logging.getLogger(__name__)


@tagged("-at_install", "post_install")
class TestWebsiteRedirect(TransactionCase):
    def test_archiving_override_cannot_expose_a_cycle(self):
        self._check_override_removal("archive")

    def test_deleting_override_cannot_expose_a_cycle(self):
        self._check_override_removal("unlink")

    def test_moving_override_url_cannot_expose_a_cycle(self):
        self._check_override_removal("rename")

    def _check_override_removal(self, operation):
        website = self.env.ref("website.default_website")
        rewrites = self.env["website.rewrite"]
        rewrites.create(
            {"name": "generic", "url_from": "/challenge-b", "url_to": "/challenge-a"}
        )
        override = rewrites.create(
            {
                "name": "override",
                "url_from": "/challenge-b",
                "url_to": "/challenge-end",
                "website_id": website.id,
            }
        )
        rewrites.create(
            {
                "name": "start",
                "url_from": "/challenge-a",
                "url_to": "/challenge-b",
                "website_id": website.id,
            }
        )
        _logger.debug(
            "Challenge: %s override %s exposes a cycle on website %s",
            operation,
            override.id,
            website.id,
        )
        with self.assertRaises(ValidationError):
            if operation == "archive":
                override.active = False
            elif operation == "unlink":
                override.unlink()
            else:
                override.url_from = "/challenge-elsewhere"

    def test_redirect_cycle_with_trailing_slash_alias_is_rejected(self):
        rewrites = self.env["website.rewrite"]
        rewrites.create(
            {"name": "first", "url_from": "/challenge-a", "url_to": "/challenge-b/"}
        )
        with self.assertRaises(ValidationError):
            rewrites.create(
                {
                    "name": "second",
                    "url_from": "/challenge-b",
                    "url_to": "/challenge-a/",
                }
            )

    def test_fragment_destination_does_not_hide_a_redirect_cycle(self):
        rewrites = self.env["website.rewrite"]
        rewrites.create(
            {
                "name": "first",
                "url_from": "/challenge-a",
                "url_to": "/challenge-b#section",
            }
        )
        with self.assertRaises(ValidationError):
            rewrites.create(
                {
                    "name": "second",
                    "url_from": "/challenge-b",
                    "url_to": "/challenge-a#section",
                }
            )

    def test_redirect_chain_validation_batches_database_reads(self):
        redirects = self.env["website.rewrite"].create(
            [
                {
                    "name": f"chain {index}",
                    "url_from": f"/audit-chain-{index}",
                    "url_to": f"/audit-chain-{index + 1}",
                }
                for index in range(25)
            ]
        )
        self.env.flush_all()
        _logger.debug(
            "Checking %s cached chain records: one candidate query and one website query",
            len(redirects),
        )
        with self.assertQueryCount(2):
            redirects._check_no_redirect_cycle()
        with self.assertRaises(ValidationError):
            redirects[-1].url_to = redirects[0].url_from

    def test_no_phantom_generic_website_is_checked(self):
        rewrites = self.env["website.rewrite"]
        rewrites.create(
            {"name": "generic b", "url_from": "/challenge-b", "url_to": "/challenge-a"}
        )
        for website in self.env["website"].search([]):
            rewrites.create(
                {
                    "name": "specific end",
                    "url_from": "/challenge-b",
                    "url_to": "/challenge-end",
                    "website_id": website.id,
                }
            )
        redirect = rewrites.create(
            {"name": "generic a", "url_from": "/challenge-a", "url_to": "/challenge-b"}
        )
        self.assertTrue(redirect.active)

    def test_redirect_cycle_preserves_query_parameters(self):
        rewrites = self.env["website.rewrite"]
        rewrites.create(
            {
                "name": "first",
                "url_from": "/challenge-a?probe=1",
                "url_to": "/challenge-b",
            }
        )
        with self.assertRaises(ValidationError):
            rewrites.create(
                {
                    "name": "second",
                    "url_from": "/challenge-b?probe=1",
                    "url_to": "/challenge-a",
                }
            )

    def test_redirect_cycle_resolves_relative_destinations(self):
        rewrites = self.env["website.rewrite"]
        rewrites.create({"name": "first", "url_from": "/challenge/a", "url_to": "b"})
        with self.assertRaises(ValidationError):
            rewrites.create(
                {"name": "second", "url_from": "/challenge/b", "url_to": "a"}
            )

    def test_route_refresh_is_idempotent_with_overlapping_routes(self):
        routes = self.env["website.route"]
        endpoint = SimpleNamespace(routing={"methods": ["GET"]})
        stale = routes.create({"path": "/audit-stale"})
        rules = [
            ("/audit-route", endpoint),
            ("/audit-route", endpoint),
            ("/audit-post", SimpleNamespace(routing={"methods": ["POST"]})),
        ]
        with patch.object(
            type(self.env["ir.http"]), "_generate_routing_rules", return_value=rules
        ):
            for refresh in range(3):
                routes._refresh()
                found = routes.search([("path", "=", "/audit-route")])
                _logger.debug("Route refresh %s produced ids %s", refresh, found.ids)
                self.assertEqual(len(found), 1)
            self.assertFalse(stale.exists())
            self.assertFalse(routes.search([("path", "=", "/audit-post")]))

    def test_routing_rewrite_can_be_archived_after_routes_are_generated(self):
        website = self.env.ref("website.default_website")
        rewrite = self.env["website.rewrite"].create(
            {
                "name": "routed",
                "redirect_type": "308",
                "url_from": "/website/info",
                "url_to": "/audit-website-info",
            }
        )
        with MockRequest(self.env, website=website):
            self.env["ir.http"].routing_map()
            rewrite.active = False
            rewrite.active = True
        self.assertTrue(rewrite.active)

    def test_specific_routing_rewrite_wins_regardless_of_creation_order(self):
        website = self.env.ref("website.default_website")
        rewrites = self.env["website.rewrite"]
        specific = rewrites.create(
            {
                "name": "specific removal",
                "redirect_type": "404",
                "url_from": "/audit-route-priority",
                "website_id": website.id,
            }
        )
        generic = specific.copy({"website_id": False, "name": "generic removal"})
        selected = self.env["ir.http"]._get_rewrites(website.id)
        _logger.debug(
            "Routing candidates specific=%s generic=%s selected=%s",
            specific.id,
            generic.id,
            selected[specific.url_from].id,
        )
        self.assertEqual(selected[specific.url_from], specific)
        self.assertEqual(
            self.env["ir.http"]._get_rewrites(False)[generic.url_from], generic
        )

    def test_archived_redirect_can_close_a_dormant_cycle(self):
        rewrites = self.env["website.rewrite"]
        rewrites.create({"name": "first", "url_from": "/audit-a", "url_to": "/audit-b"})
        dormant = rewrites.create(
            {
                "name": "dormant",
                "url_from": "/audit-b",
                "url_to": "/audit-a",
                "active": False,
            }
        )
        self.assertFalse(dormant.active)

    def test_activating_redirect_checks_for_cycles(self):
        rewrites = self.env["website.rewrite"]
        dormant = rewrites.create(
            {
                "name": "dormant",
                "url_from": "/audit-b",
                "url_to": "/audit-a",
                "active": False,
            }
        )
        rewrites.create({"name": "first", "url_from": "/audit-a", "url_to": "/audit-b"})
        _logger.debug(
            "Activating redirect %s closes /audit-a -> /audit-b -> /audit-a", dormant.id
        )
        with self.assertRaises(ValidationError):
            dormant.active = True

    def test_generic_redirect_checks_cycles_on_specific_websites(self):
        website = self.env.ref("website.default_website")
        rewrites = self.env["website.rewrite"]
        rewrites.create(
            {
                "name": "specific",
                "url_from": "/audit-b",
                "url_to": "/audit-a",
                "website_id": website.id,
            }
        )
        with self.assertRaises(ValidationError):
            rewrites.create(
                {"name": "generic", "url_from": "/audit-a", "url_to": "/audit-b"}
            )

    def test_cycle_check_uses_the_specific_redirect_over_the_generic(self):
        website = self.env.ref("website.default_website")
        rewrites = self.env["website.rewrite"]
        rewrites.create(
            {"name": "generic", "url_from": "/audit-b", "url_to": "/audit-a"}
        )
        rewrites.create(
            {
                "name": "specific",
                "url_from": "/audit-b",
                "url_to": "/audit-end",
                "website_id": website.id,
            }
        )
        redirect = rewrites.create(
            {
                "name": "start",
                "url_from": "/audit-a",
                "url_to": "/audit-b",
                "website_id": website.id,
            }
        )
        self.assertTrue(redirect.active)

    def test_moving_redirect_to_another_website_checks_for_cycles(self):
        website = self.env.ref("website.default_website")
        other = self.env["website"].create({"name": "Redirect isolation"})
        rewrites = self.env["website.rewrite"]
        rewrites.create(
            {
                "name": "first",
                "url_from": "/audit-a",
                "url_to": "/audit-b",
                "website_id": website.id,
            }
        )
        second = rewrites.create(
            {
                "name": "second",
                "url_from": "/audit-b",
                "url_to": "/audit-a",
                "website_id": other.id,
            }
        )
        with self.assertRaises(ValidationError):
            second.website_id = website

    def test_01_website_redirect_validation(self):
        with self.assertRaises(ValidationError) as error:
            self.env["website.rewrite"].create(
                {
                    "name": "Test Website Redirect",
                    "redirect_type": "308",
                    "url_from": "/website/info",
                    "url_to": "/",
                }
            )
        self.assertIn("homepage", str(error.exception))

        with self.assertRaises(ValidationError) as error:
            self.env["website.rewrite"].create(
                {
                    "name": "Test Website Redirect",
                    "redirect_type": "308",
                    "url_from": "/website/info",
                    "url_to": "/favicon.ico",
                }
            )
        self.assertIn("existing page", str(error.exception))

        with self.assertRaises(ValidationError) as error:
            self.env["website.rewrite"].create(
                {
                    "name": "Test Website Redirect",
                    "redirect_type": "308",
                    "url_from": "/website/info",
                    "url_to": "/favicon.ico/",
                }
            )
        self.assertIn("existing page", str(error.exception))

        with self.assertRaises(ValidationError) as error:
            self.env["website.rewrite"].create(
                {
                    "name": "Test Website Redirect",
                    "redirect_type": "301",
                    "url_from": "/website/info",
                    "url_to": "#",
                }
            )
        self.assertIn("must not start with '#'", str(error.exception))

        with self.assertRaises(ValidationError) as error:
            self.env["website.rewrite"].create(
                {
                    "name": "Test Website Redirect",
                    "redirect_type": "301",
                    "url_from": "/website/info",
                    "url_to": "/website/info",
                }
            )
        self.assertIn("should not be same", str(error.exception))

    def test_sitemap_with_redirect(self):
        self.env["website.rewrite"].create(
            {
                "name": "Test Website Redirect",
                "redirect_type": "308",
                "url_from": "/website/info",
                "url_to": "/test",
            }
        )
        website = self.env.ref("website.default_website")
        with MockRequest(self.env, website=website):
            self.env["website.rewrite"].refresh_routes()
            pages = self.env.ref("website.default_website")._enumerate_pages()
            urls = [url["loc"] for url in pages]
            self.assertIn("/website/info", urls)
            self.assertNotIn("/test", urls)


@tagged("-at_install", "post_install")
class TestWebsiteRedirectServe(HttpCase):
    def test_redirect_on_a_308_destination_does_not_create_a_cycle(self):
        rewrites = self.env["website.rewrite"]
        rewrites.create(
            {
                "name": "controller alias",
                "url_from": "/website/info",
                "url_to": "/challenge-info-alias",
                "redirect_type": "308",
            }
        )
        rewrites.create(
            {
                "name": "unused fallback",
                "url_from": "/challenge-info-alias",
                "url_to": "/website/info",
                "redirect_type": "301",
            }
        )
        response = self.url_open("/website/info", allow_redirects=False)
        self.assertEqual(response.status_code, 308)
        self.assertEqual(
            self.url_open("/challenge-info-alias", allow_redirects=False).status_code,
            200,
        )

    def test_specific_308_survives_a_later_generic_404(self):
        website = self.env.ref("website.default_website")
        rewrites = self.env["website.rewrite"]
        rewrites.create(
            {
                "name": "specific redirect",
                "url_from": "/website/info",
                "url_to": "/challenge-website-info",
                "redirect_type": "308",
                "website_id": website.id,
            }
        )
        rewrites.create(
            {
                "name": "generic removal",
                "url_from": "/website/info",
                "redirect_type": "404",
            }
        )
        response = self.url_open("/website/info", allow_redirects=False)
        _logger.debug(
            "Challenge 308 vs 404: status=%s location=%s",
            response.status_code,
            response.headers.get("Location"),
        )
        self.assertEqual(response.status_code, 308)
        self.assertTrue(
            response.headers["Location"].endswith("/challenge-website-info")
        )
        self.assertEqual(self.url_open("/challenge-website-info").status_code, 200)

    def test_specific_website_redirect_wins_over_generic(self):
        Rewrite = self.env["website.rewrite"]
        website = self.env["website"].browse(1)
        Rewrite.create(
            {
                "name": "generic",
                "redirect_type": "301",
                "url_from": "/promo-priority",
                "url_to": "/generic-target",
                "website_id": False,
            }
        )
        Rewrite.create(
            {
                "name": "specific",
                "redirect_type": "301",
                "url_from": "/promo-priority",
                "url_to": "/specific-target",
                "website_id": website.id,
            }
        )
        res = self.url_open("/promo-priority", allow_redirects=False)
        self.assertEqual(res.status_code, 301)
        self.assertTrue(
            res.headers.get("Location", "").endswith("/specific-target"),
            "website-specific 301 must win over the generic one, got %r"
            % res.headers.get("Location"),
        )


@tagged("-at_install", "post_install")
class TestWebsiteRewriteOrdering(TransactionCase):
    def _rewrite(self, name, **values):
        return self.env["website.rewrite"].create(
            {
                "name": name,
                "redirect_type": "301",
                "url_from": f"/from-{name}",
                "url_to": f"/to-{name}",
                **values,
            }
        )

    def test_rewrites_come_back_in_the_order_they_were_dragged_into(self):
        """`website_rewrite.xml` puts `widget="handle"` on the redirect list, so
        the drag writes `sequence`; without `_order` naming it the list
        re-rendered in id order and the reordering did nothing.

        Routing is unaffected either way: `ir_http._get_rewrites` passes its own
        `order="website_id DESC, id"`.
        """
        rewrites = (
            self._rewrite("third", sequence=30)
            | self._rewrite("second", sequence=20)
            | self._rewrite("first", sequence=10)
        )
        self.env.flush_all()
        self.env.invalidate_all()

        found = self.env["website.rewrite"].search([("id", "in", rewrites.ids)])

        self.assertEqual(found.mapped("name"), ["first", "second", "third"])

    def test_rewrites_at_the_default_sequence_keep_a_stable_order(self):
        Rewrite = self.env["website.rewrite"]
        tied = Rewrite.browse()
        for index in range(6):
            tied |= self._rewrite(f"tied-{index}")
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(len(set(tied.mapped("sequence"))), 1, "the fixture must tie")

        orders = [Rewrite.search([("id", "in", tied.ids)]).ids for _ in range(4)]

        self.assertEqual(orders[0], sorted(tied.ids))
        self.assertTrue(all(order == orders[0] for order in orders))
