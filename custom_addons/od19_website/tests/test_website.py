from datetime import timedelta

from odoo import Command, fields, http
from odoo.tests import tagged
from odoo.tests.common import (
    HOST,
    HttpCase,
    Opener,
    TransactionCase,
    get_db_name,
)

from odoo.addons.od19_website.models.website import (
    OD19_ORG_EMAIL,
    OD19_ORG_NAME,
    OD19_ORG_PHONE,
)


class TestWebsite(TransactionCase):
    """Basic tests for website company configuration fields."""

    def test_company_has_website_fields(self):
        company = self.env.user.company_id
        # Check default values are set
        self.assertEqual(company.od19_website_primary_color, "#9E2424")
        self.assertEqual(company.od19_website_secondary_color, "#f39200")
        self.assertTrue(company.od19_website_tagline)
        self.assertTrue(company.od19_website_hero_title)

    def test_company_website_fields_writable(self):
        company = self.env.user.company_id
        company.write({
            "od19_website_tagline": "New Tagline",
            "od19_website_primary_color": "#123456",
            "od19_website_secondary_color": "#654321",
            "od19_website_hero_title": "New Hero Title",
            "od19_website_hero_subtitle": "New Hero Subtitle",
            "od19_website_facebook_url": "https://facebook.com/test",
            "od19_website_linkedin_url": "https://linkedin.com/test",
            "od19_website_youtube_url": "https://youtube.com/test",
        })
        self.assertEqual(company.od19_website_tagline, "New Tagline")
        self.assertEqual(company.od19_website_primary_color, "#123456")
        self.assertEqual(company.od19_website_facebook_url, "https://facebook.com/test")


@tagged("post_install", "-at_install")
class TestWebsiteLanguageSwitch(HttpCase):
    """The navbar must expose a one-click EN | ไทย switch."""

    def test_language_switch_visible_with_two_languages(self):
        website = self.env["website"].get_current_website()
        thai = self.env["res.lang"]._activate_lang("th_TH")
        website.language_ids = website.language_ids | thai

        html = self.url_open("/").text

        self.assertIn("od19-lang-switch", html)
        # The switch is rendered once per header (desktop navbar + mobile
        # offcanvas), so every language option shows up at least once.
        self.assertGreaterEqual(html.count("od19-lang-opt"), 2)
        # Both languages are exposed as one-click options.
        self.assertIn('data-url_code="en"', html)
        self.assertIn('data-url_code="th"', html)


@tagged("post_install", "-at_install")
class TestEmployeePortalBooking(HttpCase):
    """The employee portal must expose the meeting-room booking panel."""

    def test_booking_panel_renders(self):
        thai = self.env["res.lang"]._activate_lang("th_TH")
        website = self.env["website"].get_current_website()
        website.language_ids = website.language_ids | thai

        tester = self.env["res.users"].create({
            "name": "Portal Tester",
            "login": "od19_portal_tester",
            "email": "od19.portal.tester@example.com",
            "group_ids": [Command.link(self.env.ref("base.group_user").id)],
        })
        # HttpCase patches the credential check, so only the login must exist.
        self.authenticate(tester.login, "test")

        # The panel renders one live tile per active room, so seed one instead
        # of relying on demo data being present in the test database.
        self.env["od19.meeting.room"].create({
            "name": "Portal Test Room",
            "capacity": 6,
        })

        html = self.url_open("/employee-portal").text

        # Live status tile per meeting room.
        self.assertGreaterEqual(html.count("od19-room-tile"), 1)
        # The compact booking form posts to the portal controller.
        self.assertIn("od19-booking-form", html)
        self.assertIn("/employee-portal/book-room", html)

    def _portal_tester(self, login):
        thai = self.env["res.lang"]._activate_lang("th_TH")
        website = self.env["website"].get_current_website()
        website.language_ids = website.language_ids | thai

        tester = self.env["res.users"].create({
            "name": login,
            "login": login,
            "email": "%s@example.com" % login,
            "group_ids": [Command.link(self.env.ref("base.group_user").id)],
        })
        # HttpCase patches the credential check, so only the login must exist.
        self.authenticate(tester.login, "test")
        return tester

    def test_room_tile_opens_schedule_popup(self):
        """Clicking a room must reveal when that room is already taken."""
        self._portal_tester("od19_portal_popup_tester")
        room = self.env["od19.meeting.room"].create({
            "name": "Popup Test Room",
            "capacity": 4,
        })

        html = self.url_open("/employee-portal").text

        # The tile is a modal trigger and the popup carries a lazy-loaded slot
        # that the frontend fills once the modal is shown.
        self.assertIn("od19-room-modal-%s" % room.id, html)
        self.assertIn("od19-room-schedule", html)
        self.assertIn("od19-room-hint", html)
        self.assertIn('data-bs-toggle="modal"', html)
        # The date picker is bounded on both ends of the booking window.
        self.assertIn("min=", html)
        self.assertIn("max=", html)

    def test_room_schedule_endpoint_returns_window(self):
        """The popup endpoint reports the room schedule as JSON."""
        tester = self._portal_tester("od19_portal_json_tester")
        room = self.env["od19.meeting.room"].create({
            "name": "JSON Test Room",
            "capacity": 4,
        })
        start_dt = fields.Datetime.now() + timedelta(days=3)
        self.env["od19.meeting.room.booking"].create({
            "name": "Upcoming Booking",
            "room_id": room.id,
            "organizer_id": tester.id,
            "participant_count": 2,
            "start_datetime": start_dt,
            "end_datetime": start_dt + timedelta(hours=1),
        })

        response = self.url_open(
            "/employee-portal/room-schedule?room_id=%s" % room.id
        )
        response.raise_for_status()
        payload = response.json()

        # The popup looks the same six months back as it does forward.
        self.assertEqual(payload["window_months"], 6)
        self.assertEqual(payload["room"]["id"], room.id)
        self.assertEqual(len(payload["upcoming"]), 1)
        self.assertEqual(payload["upcoming"][0]["name"], "Upcoming Booking")
        self.assertEqual(payload["upcoming"][0]["state_label"], "จองแล้ว")


@tagged("post_install", "-at_install")
class TestEmployeeLoginRedirect(HttpCase):
    """Employees land on the portal after login; everyone else keeps /odoo."""

    def setUp(self):
        super().setUp()
        self.session = http.root.session_store.new()
        self.session.update(http.get_default_session(), db=get_db_name())
        self.opener = Opener(self)
        self.opener.cookies.set("session_id", self.session.sid, domain=HOST, path="/")

    def _login(self, login, password):
        response = self.url_open("/web/login", data={
            "login": login,
            "password": password,
            "csrf_token": http.Request.csrf_token(self),
        })
        response.raise_for_status()
        return response

    def _make_user(self, login, *, with_employee):
        vals = {
            "name": login,
            "login": login,
            "password": login,
            "group_ids": [Command.link(self.env.ref("base.group_user").id)],
        }
        user = self.env["res.users"].create(vals)
        if with_employee:
            # ``res.users.employee_id`` is a non-stored compute filled from the
            # employees whose ``user_id`` points at the user, so the employee
            # has to be created on that side (writing ``employee_id`` directly
            # does nothing).
            self.env["hr.employee"].create({"name": login, "user_id": user.id})
            user.invalidate_recordset(["employee_id"])
        return user

    def test_employee_login_lands_on_portal(self):
        user = self._make_user("od19_login_employee", with_employee=True)
        response = self._login(user.login, user.login)
        self.assertEqual(response.request.path_url, "/employee-portal")

    def test_other_login_lands_on_backend(self):
        user = self._make_user("od19_login_plain", with_employee=False)
        response = self._login(user.login, user.login)
        self.assertEqual(response.request.path_url, "/odoo")


@tagged("post_install", "-at_install")
class TestBrandFoundation(HttpCase):
    """SP1: fixed brand logo + branded 404 page."""

    def test_header_uses_autoinfo_logo_svg(self):
        """The homepage header must render autoinfo_logo.svg as the logo."""
        html = self.url_open("/").text
        self.assertIn("autoinfo_logo.svg", html)

    def test_favicon_is_present(self):
        """Favicon link must point at the module favicon."""
        html = self.url_open("/").text
        self.assertIn("/od19_website/static/src/img/favicon.svg", html)

    def test_404_page_is_branded(self):
        """A non-existent URL returns the Auto-Info branded 404 page."""
        response = self.url_open("/this-page-does-not-exist-12345")
        self.assertEqual(response.status_code, 404)
        html = response.text
        # Branded elements from od19_404 template
        self.assertIn("od19-404-wrap", html)
        self.assertIn("autoinfo_logo.svg", html)
        self.assertIn("404", html)
        # Link back home must be present
        self.assertIn('href="/"', html)


@tagged("post_install", "-at_install")
class TestNavigationIA(HttpCase):
    """SP2: public navigation excludes staff links, inner pages carry breadcrumbs."""

    def test_employee_portal_not_in_public_nav(self):
        """The staff-only /employee-portal page must not be a public menu item."""
        # The legacy menu record is either never declared (fresh install) or
        # removed by website.menu.od19_configure_menus() (upgrade).
        self.assertFalse(
            self.env.ref(
                "od19_website.menu_employee_portal", raise_if_not_found=False
            )
        )
        website = self.env["website"].get_current_website()
        portal_menus = website.menu_id.child_id.filtered(
            lambda m: (m.url or "").strip().rstrip("/") == "/employee-portal"
        )
        self.assertFalse(portal_menus, "Employee Portal must not be a top nav item")

    def test_footer_has_employee_portal_link(self):
        """Staff still reach the portal through the discreet footer link."""
        html = self.url_open("/").text
        self.assertIn('class="od19-footer-staff"', html)
        self.assertIn('href="/employee-portal"', html)

    def test_inner_pages_have_breadcrumb(self):
        """Every inner content page exposes a breadcrumb linked back home."""
        for path in (
            "/industrial-automation",
            "/building-automation",
            "/terminal-automation",
            "/products",
            "/about-us",
            "/quality-certifications",
            "/portfolio",
        ):
            html = self.url_open(path).text
            self.assertIn(
                '<nav class="od19-breadcrumb">',
                html,
                "missing breadcrumb on %s" % path,
            )
            self.assertIn(
                '<a href="/">Home</a>',
                html,
                "breadcrumb on %s must link back home" % path,
            )


@tagged("post_install", "-at_install")
class TestHomepageSP3(HttpCase):
    """SP3: homepage hero polish, process narrative and animated stats."""

    def test_homepage_hero_has_sheen_and_scroll_cue(self):
        """The hero carries the animated sheen layer and a scroll cue to services."""
        html = self.url_open("/").text
        self.assertIn("od19-home-hero", html)
        self.assertIn("od19-hero-sheen", html)
        self.assertIn('class="od19-hero-scroll"', html)
        self.assertIn('href="#services"', html)

    def test_homepage_has_process_section(self):
        """"How We Work" tells the four-step delivery story."""
        html = self.url_open("/").text
        self.assertIn('id="how-we-work"', html)
        self.assertGreaterEqual(
            html.count("od19-step-num"),
            4,
            "the process section must render four numbered steps",
        )

    def test_homepage_stats_are_countup_ready(self):
        """Every stat number exposes the data hooks used by od19_home.js."""
        html = self.url_open("/").text
        self.assertGreaterEqual(
            html.count("data-od19-count"),
            4,
            "all four stats must be animatable",
        )

    def test_homepage_section_anchors(self):
        """Every main block is deep-linkable through a stable anchor id."""
        html = self.url_open("/").text
        for anchor in (
            "services",
            "how-we-work",
            "about",
            "products",
            "partners",
            "news",
            "careers",
            "contact",
        ):
            self.assertIn('id="%s"' % anchor, html, "missing anchor #%s" % anchor)


@tagged("post_install", "-at_install")
class TestProductsServicesSP4(HttpCase):
    """SP4: products catalog and service pages share one content source."""

    def test_catalog_is_single_source_of_truth(self):
        """The catalog lives on the website model and covers three domains."""
        products = self.env["website"].od19_products()
        self.assertEqual(len(products), 25)
        by_dept = {}
        for product in products:
            by_dept[product["dept"]] = by_dept.get(product["dept"], 0) + 1
        self.assertEqual(by_dept, {"industrial": 9, "building": 8, "terminal": 8})

    def test_products_page_shows_filter_counts(self):
        """Each filter pill is labelled with the live number of products."""
        html = self.url_open("/products").text
        self.assertEqual(html.count("od19-pc-count"), 4)
        for count in ("25", "9", "8"):
            self.assertIn(
                'class="od19-pc-count">%s<' % count,
                html,
                "missing filter count %s" % count,
            )

    def test_products_page_links_to_service_pages(self):
        """Every department links through to its service page."""
        html = self.url_open("/products").text
        for url in (
            "/industrial-automation",
            "/building-automation",
            "/terminal-automation",
        ):
            self.assertIn('href="%s"' % url, html, "missing cross-link to %s" % url)
        self.assertEqual(html.count("od19-pc-dept-link"), 3)

    def test_products_hero_stats_reflect_catalog(self):
        """Hero stats are derived from the catalog, not hard-coded."""
        html = self.url_open("/products").text
        self.assertIn("25+", html)
        self.assertIn("<span>Product Brands</span>", html)
        self.assertNotIn("Global Brands", html)

    def test_service_pages_have_related_products(self):
        """Each service page cross-links back to the shared catalog."""
        for path in (
            "/industrial-automation",
            "/building-automation",
            "/terminal-automation",
        ):
            html = self.url_open(path).text
            self.assertGreaterEqual(
                html.count("od19-rel-card"),
                4,
                "%s must show at least four related products" % path,
            )
            self.assertIn(
                'href="/products"',
                html,
                "%s must link back to the catalog" % path,
            )


@tagged("post_install", "-at_install")
class TestTrustReferencesSP5(HttpCase):
    """SP5: quality-certifications and portfolio share one content source."""

    def test_trust_content_is_single_source_of_truth(self):
        """Certifications and references both live on the website model."""
        certs = self.env["website"].od19_certifications()
        self.assertEqual(
            [c["key"] for c in certs],
            ["iso9001", "iso14001", "gmp", "csv"],
        )

        projects = self.env["website"].od19_projects()
        self.assertEqual(len(projects), 9)
        by_sector = {}
        for project in projects:
            by_sector[project["sector"]] = by_sector.get(project["sector"], 0) + 1
        self.assertEqual(by_sector, {"industrial": 3, "building": 3, "terminal": 3})

    def test_quality_page_renders_certifications(self):
        """/quality-certifications shows every certificate with a status badge."""
        html = self.url_open("/quality-certifications").text
        self.assertGreaterEqual(html.count("od19-cert-card"), 4)
        self.assertIn("ISO 9001:2015", html)
        self.assertIn("ISO 14001", html)
        # Status badges are driven by each certificate's status field.
        self.assertIn("od19-cert-certified", html)
        self.assertIn("od19-cert-in_progress", html)
        self.assertEqual(
            html.count("od19-accred-chip"),
            len(self.env["website"].od19_accreditations()),
        )

    def test_quality_page_shows_configured_certificate(self):
        """Certificate body / number appear only once set in the backend."""
        company = self.env["website"].get_current_website().company_id
        company.write({
            "od19_website_cert_body": "SGS (Thailand) Ltd.",
            "od19_website_cert_no": "TH-QM-12345",
        })
        # The page response is cached for anonymous visitors for an hour and a
        # company write does not invalidate that cache, so drop it before each
        # fetch to observe the current backend values.
        self.env.registry.clear_cache()
        html = self.url_open("/quality-certifications").text
        self.assertIn("od19-cert-body", html)
        self.assertIn("SGS (Thailand) Ltd.", html)
        self.assertIn("od19-cert-no", html)
        self.assertIn("TH-QM-12345", html)

        # With no certificate on file the page invites the visitor to ask.
        company.write({
            "od19_website_cert_body": False,
            "od19_website_cert_no": False,
            "od19_website_cert_valid_until": False,
        })
        self.env.registry.clear_cache()
        html = self.url_open("/quality-certifications").text
        self.assertIn("od19-cert-request", html)

    def test_portfolio_page_renders_grid_and_filter(self):
        """/portfolio shows the reference grid with a live sector filter."""
        html = self.url_open("/portfolio").text
        self.assertEqual(html.count("od19-proj-card"), 9)
        self.assertEqual(html.count("od19-pc-pill"), 4)
        self.assertEqual(html.count("od19-pc-count"), 4)
        for count in ("9", "3"):
            self.assertIn(
                'class="od19-pc-count">%s<' % count,
                html,
                "missing filter count %s" % count,
            )
        for sector in ("industrial", "building", "terminal"):
            self.assertEqual(
                html.count('data-dept="%s"' % sector),
                3,
                "sector %s must list three references" % sector,
            )

    def test_new_pages_are_linked_from_home_about_and_footer(self):
        """Home, About and the footer all link to the two new trust pages."""
        for path in ("/", "/about-us"):
            html = self.url_open(path).text
            self.assertIn(
                'href="/quality-certifications"',
                html,
                "%s must link to the quality page" % path,
            )
            self.assertIn(
                'href="/portfolio"',
                html,
                "%s must link to the references page" % path,
            )


@tagged("post_install", "-at_install")
class TestContactRFQSP6(HttpCase):
    """SP6: the contact page posts a real crm.lead and is routed by enquiry."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # A "Service" team does not exist on a fresh database; create one so the
        # enquiry -> team routing can be asserted end to end.
        cls.service_team = cls.env["crm.team"].create({"name": "Service"})

    def test_enquiry_types_are_single_source_of_truth(self):
        """The RFQ enquiry types live on the website model."""
        types = self.env["website"].od19_enquiry_types()
        self.assertEqual(len(types), 7)
        self.assertEqual(
            [t["key"] for t in types],
            ["quotation", "product", "service", "spare_part",
             "certificate", "career", "other"],
        )
        for etype in types:
            self.assertTrue(etype["label"])
            self.assertTrue(etype["team"])
            self.assertTrue(etype["tag"])

    def test_contact_page_renders_rfq_form(self):
        """/contactus exposes the RFQ form that posts to crm.lead."""
        html = self.url_open("/contactus").text
        self.assertIn('data-model_name="crm.lead"', html)
        self.assertIn('data-success-page="/contactus-thank-you"', html)
        self.assertIn("od19-rfq-form", html)
        self.assertIn('name="Enquiry Type"', html)
        self.assertIn('name="Product of Interest"', html)
        for etype in self.env["website"].od19_enquiry_types():
            self.assertIn(etype["label"], html)
        for product in self.env["website"].od19_products():
            self.assertIn(product["name"], html)

    def test_rfq_creates_lead_and_routes_by_enquiry(self):
        """Posting the RFQ creates a crm.lead routed to the matching team/tag."""
        self.authenticate(None, None)
        response = self.url_open("/website/form/crm.lead", data={
            "contact_name": "Somchai Jaidee",
            "partner_name": "ACME Manufacturing",
            "email_from": "somchai@acme.co.th",
            "phone": "+66 81 234 5678",
            "Enquiry Type": "service",
            "Product of Interest": "Modicon M580",
            "description": "Please quote a preventive-maintenance contract.",
            "PDPA Consent": "yes",
            "csrf_token": http.Request.csrf_token(self),
        })
        lead_id = response.json().get("id")
        self.assertTrue(lead_id, "the RFQ must create a crm.lead")

        lead = self.env["crm.lead"].sudo().browse(lead_id)
        self.assertTrue(lead.exists())
        self.assertEqual(lead.contact_name, "Somchai Jaidee")
        self.assertEqual(lead.email_from, "somchai@acme.co.th")
        self.assertEqual(lead.team_id, self.service_team)
        self.assertIn("Website: Service", lead.tag_ids.mapped("name"))
        self.assertIn("Service", lead.name)

    def test_quotation_routes_to_default_sales_team(self):
        """A quotation enquiry lands on the default 'Sales' team."""
        self.authenticate(None, None)
        response = self.url_open("/website/form/crm.lead", data={
            "contact_name": "Kanya W.",
            "email_from": "kanya@example.co.th",
            "Enquiry Type": "quotation",
            "description": "We need a quotation for a new line.",
            "csrf_token": http.Request.csrf_token(self),
        })
        lead = self.env["crm.lead"].sudo().browse(response.json().get("id"))
        self.assertTrue(lead.exists())
        self.assertEqual(lead.team_id.name, "Sales")
        self.assertIn("Website: Quotation", lead.tag_ids.mapped("name"))

    def test_thank_you_page_shows_auto_info_not_placeholder(self):
        """/contactus-thank-you shows Auto-Info details, not the Odoo demo data."""
        html = self.url_open("/contactus-thank-you").text
        self.assertNotIn("3575 Fake Buena Vista Avenue", html)
        self.assertNotIn("+1 555-555-5556", html)
        self.assertIn("1359 Soi Ladprao 94", html)
        self.assertIn("sales@auto-info.co.th", html)


@tagged("post_install", "-at_install")
class TestSeoAnalyticsSP7(HttpCase):
    """SP7: every page is index-ready — meta copy, schema.org, OG, robots,
    sitemap and a consent-gated Google Analytics tag."""

    OD19_SEO_PAGES = [
        "/",
        "/industrial-automation",
        "/building-automation",
        "/terminal-automation",
        "/products",
        "/about-us",
        "/quality-certifications",
        "/portfolio",
    ]

    def test_every_page_has_meta_copy(self):
        """All eight pages carry a non-empty title, description and keywords."""
        pages = self.env["website.page"].search([("url", "in", self.OD19_SEO_PAGES)])
        self.assertEqual(len(pages), len(self.OD19_SEO_PAGES))
        for page in pages:
            self.assertTrue(
                page.website_meta_title, "%s is missing a meta title" % page.url,
            )
            self.assertTrue(
                page.website_meta_description,
                "%s is missing a meta description" % page.url,
            )
            self.assertTrue(
                page.website_meta_keywords,
                "%s is missing meta keywords" % page.url,
            )

    def test_homepage_renders_title_and_meta(self):
        """Rendering / emits the page title, description and keywords."""
        page = self.env["website.page"].search([("url", "=", "/")], limit=1)
        html = self.url_open("/").text

        self.assertIn("<title>%s</title>" % page.website_meta_title, html)
        self.assertIn('name="description"', html)
        self.assertIn('name="keywords"', html)
        self.assertIn(page.website_meta_description, html)
        self.assertIn(page.website_meta_keywords, html)

    def test_jsonld_and_social_meta_on_every_page(self):
        """Every page emits Organization + WebSite JSON-LD and social tags."""
        for path in self.OD19_SEO_PAGES:
            html = self.url_open(path).text
            self.assertIn(
                'type="application/ld+json"', html,
                "%s must carry schema.org markup" % path,
            )
            self.assertIn('"@type": "Organization"', html, path)
            self.assertIn('"@type": "WebSite"', html, path)
            # The published identity is the canonical Auto-Info one — never the
            # res.company record, which could still hold Odoo's demo values.
            self.assertIn('"name": "%s"' % OD19_ORG_NAME, html, path)
            self.assertIn('"telephone": "%s"' % OD19_ORG_PHONE, html, path)
            self.assertIn('"email": "%s"' % OD19_ORG_EMAIL, html, path)
            # Social sharing tags (OpenGraph + Twitter) plus the locale hint.
            for tag in ('property="og:title"', 'property="og:site_name"',
                        'property="og:image"', 'property="og:locale"',
                        'name="twitter:card"'):
                self.assertIn(tag, html, "%s must expose %s" % (path, tag))

    def test_robots_txt_blocks_private_areas(self):
        """/robots.txt keeps the backend, portal and employee area out."""
        body = self.url_open("/robots.txt").text
        self.assertIn("Disallow: /employee-portal", body)
        self.assertIn("Disallow: /web/", body)
        self.assertIn("Sitemap:", body)

    def test_sitemap_lists_public_pages(self):
        """/sitemap.xml exposes the public static pages."""
        xml = self.url_open("/sitemap.xml").text
        for path in ("/products", "/quality-certifications", "/contactus"):
            self.assertIn(
                path, xml, "%s must be present in the sitemap" % path,
            )

    def test_google_analytics_is_consent_gated(self):
        """A configured GA key loads gtag with analytics denied by default."""
        website = self.env["website"].get_current_website()
        # Consent gating only exists when the cookie bar is enabled — without
        # it Odoo considers every consent already granted.
        website.write({"google_analytics_key": "G-TEST1234", "cookies_bar": True})
        self.env.registry.clear_cache()

        html = self.url_open("/").text
        self.assertIn("googletagmanager.com/gtag/js?id=G-TEST1234", html)
        self.assertIn("'analytics_storage': 'denied'", html)
        self.assertIn("optionalCookiesAccepted", html)

    def test_setup_seo_is_idempotent(self):
        """od19_setup_seo() seeds defaults and never clobbers custom values."""
        website = self.env["website"].get_current_website()
        company = website.company_id
        website.write({"robots_txt": False, "google_analytics_key": False})
        company.od19_website_ga_key = "G-IDEMPOTENT1"

        self.env["website"].od19_setup_seo()
        seeded_robots = website.robots_txt
        self.assertIn("Disallow: /employee-portal", seeded_robots)
        self.assertEqual(website.google_analytics_key, "G-IDEMPOTENT1")

        # Running it again leaves the seeded values untouched.
        self.env["website"].od19_setup_seo()
        self.assertEqual(website.robots_txt, seeded_robots)
        self.assertEqual(website.google_analytics_key, "G-IDEMPOTENT1")

        # A customised robots.txt survives a re-run.
        website.write({"robots_txt": "User-agent: *\nDisallow:\n"})
        self.env["website"].od19_setup_seo()
        self.assertEqual(website.robots_txt, "User-agent: *\nDisallow:\n")


@tagged("post_install", "-at_install")
class TestPdpaLegalSP8(HttpCase):
    """SP8: the legal layer — PDPA privacy notice, terms, cookie consent and
    the go-live checks that tie them together."""

    OD19_LEGAL_PAGES = ["/privacy", "/terms"]

    def test_legal_pages_render(self):
        """/privacy and /terms are live pages with real legal copy."""
        privacy_html = self.url_open("/privacy").text
        self.assertIn("Privacy Policy", privacy_html)
        self.assertIn("Personal Data Protection Act", privacy_html)
        self.assertIn("Your rights as a data subject", privacy_html)
        self.assertIn("privacy@auto-info.co.th", privacy_html)

        terms_html = self.url_open("/terms").text
        self.assertIn("Terms of Use", terms_html)
        self.assertIn("Governing law", terms_html)

    def test_privacy_page_has_no_placeholder_data(self):
        """The privacy notice never leaks Odoo's demo company identity."""
        html = self.url_open("/privacy").text
        self.assertNotIn("+1 555-555-5556", html)
        self.assertNotIn("YourCompany", html)
        self.assertIn("1359 Soi Ladprao 94", html)

    def test_footer_links_to_legal_pages(self):
        """The footer exposes the privacy, terms and cookie policies."""
        html = self.url_open("/").text
        self.assertIn('href="/privacy"', html)
        self.assertIn('href="/terms"', html)
        self.assertIn('href="/cookie-policy"', html)

    def test_legal_pages_have_meta_and_are_in_the_sitemap(self):
        """Legal pages carry meta copy and are index-ready (go-live)."""
        pages = self.env["website.page"].search([("url", "in", self.OD19_LEGAL_PAGES)])
        self.assertEqual(len(pages), len(self.OD19_LEGAL_PAGES))
        for page in pages:
            self.assertTrue(page.is_published, "%s must be published" % page.url)
            self.assertTrue(page.website_indexed, "%s must be indexable" % page.url)
            self.assertTrue(page.website_meta_title, "%s meta title" % page.url)
            self.assertTrue(page.website_meta_description, "%s meta description" % page.url)

        xml = self.url_open("/sitemap.xml").text
        for path in self.OD19_LEGAL_PAGES:
            self.assertIn(path, xml, "%s must be listed in the sitemap" % path)

    def test_robots_txt_does_not_block_legal_pages(self):
        """/privacy and /terms stay crawlable (go-live)."""
        body = self.url_open("/robots.txt").text
        self.assertNotIn("Disallow: /privacy", body)
        self.assertNotIn("Disallow: /terms", body)

    def test_setup_pdpa_enables_consent_and_cookie_policy(self):
        """od19_setup_pdpa() turns on the cookie bar and its policy page."""
        website = self.env["website"].get_current_website()
        website.write({"cookies_bar": False})
        self.env["website.page"].search([("url", "=", "/cookie-policy")]).unlink()

        self.env["website"].od19_setup_pdpa()

        self.assertTrue(website.cookies_bar)
        cookie_policy = self.env["website.page"].search(
            [("url", "=", "/cookie-policy")], limit=1,
        )
        self.assertTrue(cookie_policy.exists())

        html = self.url_open("/cookie-policy").text
        self.assertIn("Analytics cookies", html)
        self.assertIn('href="/privacy"', html)

    def test_setup_pdpa_is_idempotent(self):
        """Re-running the PDPA setup leaves established values untouched."""
        website = self.env["website"].get_current_website()
        self.env["website"].od19_setup_pdpa()
        cookie_policy = self.env["website.page"].search(
            [("url", "=", "/cookie-policy")], limit=1,
        )
        seeded_title = cookie_policy.website_meta_title

        # A customised value must survive a re-run.
        cookie_policy.website_meta_description = "Custom notice"
        self.env["website"].od19_setup_pdpa()

        self.assertTrue(website.cookies_bar)
        self.assertEqual(cookie_policy.website_meta_title, seeded_title)
        self.assertEqual(cookie_policy.website_meta_description, "Custom notice")

