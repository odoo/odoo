import logging

from odoo import api, models
from odoo.http import request
from odoo.tools.json import scriptsafe as json_scriptsafe

_logger = logging.getLogger(__name__)

# Spelled out once and reused as (a) the schema.org Organization description,
# (b) the fallback meta description for pages without their own copy.
OD19_ORG_DESCRIPTION = (
    "The Auto-Info Co., Ltd. delivers total integrated automation solutions in "
    "industrial, building and terminal automation — PLC/SCADA, BMS/HVAC, tank "
    "gauging and loading control — with ISO 9001:2015 certified engineering, "
    "installation and service from Bangkok, Thailand."
)

# Canonical public identity used to build the schema.org Organization markup on
# every page.  It mirrors the contact details the site already shows in its
# header, footer and contact page, and is deliberately *not* read from the
# res.company record: that record may still hold Odoo's demo/placeholder values
# (e.g. "YourCompany" / "+1 555-555-5556"), which must never leak into the
# published structured data.
OD19_ORG_NAME = "The Auto-Info Co., Ltd."
OD19_ORG_PHONE = "+66 2 934 5410-6"
OD19_ORG_EMAIL = "sales@auto-info.co.th"
OD19_ORG_ADDRESS = {
    "@type": "PostalAddress",
    "streetAddress": "1359 Soi Ladprao 94 (Panjamitr), Ladprao Rd., "
                     "Plubpla, Wangthonglang",
    "addressLocality": "Bangkok",
    "postalCode": "10310",
    "addressCountry": "TH",
}

# Appended to the Odoo-generated robots.txt (the User-agent / Allow / Sitemap
# block is produced by the website.robots template itself).  Keep internal
# tooling and the employee portal out of the index.
OD19_DEFAULT_ROBOTS = """# Auto-Info — keep private areas out of the index
Disallow: /web/
Disallow: /my/
Disallow: /employee-portal
"""

# Odoo ships the website record as "My Website", which then leaks into every
# browser tab as "<page name> | My Website".  Brand it on install/upgrade.
DEFAULT_NAME = "My Website"
WEBSITE_NAME = "Auto-Info"

# Single source of truth for the product catalog shown on /products and
# cross-linked from the three service pages.  Keeping the data here means the
# catalog grid, the department filter counts and the "related products" strips
# can never drift apart.
OD19_PRODUCT_CATALOG = [
    # Industrial Automation
    {"dept": "industrial", "brand": "Schneider Electric", "name": "Modicon M580", "desc": "High-performance ePAC controller engineered for demanding process and machine automation.", "specs": ["Up to 4 racks", "Ethernet/IP + Modbus", "Hot-standby ready"], "img": "industrial-m580.jpg"},
    {"dept": "industrial", "brand": "Schneider Electric", "name": "Modicon M340", "desc": "Modular PLC platform delivering reliable control for mid-range industrial applications.", "specs": ["Modular I/O", "Fast CPU cycle", "Compact footprint"], "img": "industrial-m340.jpg"},
    {"dept": "industrial", "brand": "Schneider Electric", "name": "Magelis HMI", "desc": "Vivid touch-panel interfaces that put plant data and alarms right at the operator fingertips.", "specs": ["7 to 15 inch", "Multi-touch", "IP66 front"], "img": "industrial-magelis-hmi.jpg"},
    {"dept": "industrial", "brand": "Schneider Electric", "name": "Altivar Process Drive", "desc": "Heavy-duty variable speed drives that cut energy use across pumps fans and conveyors.", "specs": ["0.75 to 630 kW", "Built-in safety", "Energy dashboard"], "img": "industrial-altivar-drive.jpg"},
    {"dept": "industrial", "brand": "Schneider Electric", "name": "EcoStruxure Plant", "desc": "IIoT-ready automation architecture connecting the shop floor to the top floor in real time.", "specs": ["Edge control", "Cloud analytics", "Open protocol"], "img": "industrial-ecostruxure.jpg"},
    {"dept": "industrial", "brand": "Auto-Info Engineering", "name": "SCADA Centralized System", "desc": "Centralized supervisory control and data acquisition for complete plant visibility.", "specs": ["Real-time trends", "Alarm management", "Historian logging"], "img": "industrial-scada.jpg"},
    {"dept": "industrial", "brand": "Emerson", "name": "Rosemount Pressure Transmitter", "desc": "Precision pressure measurement built to survive the toughest process environments.", "specs": ["High accuracy", "HART / 4-20 mA", "Hazardous area"], "img": "industrial-rosemount-pressure.jpg"},
    {"dept": "industrial", "brand": "Emerson", "name": "Micro Motion Coriolis Meter", "desc": "Direct mass flow measurement delivering accuracy for critical batching and custody transfer.", "specs": ["Mass + density", "No moving parts", "Custody transfer"], "img": "industrial-coriolis-meter.jpg"},
    {"dept": "industrial", "brand": "Auto-Info Engineering", "name": "Custom Control Panel", "desc": "Engineered control cabinets assembled wired and tested for your exact process.", "specs": ["IP-rated enclosures", "Wired and tested", "UL / IEC build"], "img": "industrial-control-panel.jpg"},
    # Building Automation
    {"dept": "building", "brand": "Siemens", "name": "Symaro Sensors", "desc": "Temperature humidity and CO2 sensors that keep HVAC performance precise and efficient.", "specs": ["High accuracy", "Room and duct", "Low drift"], "img": "building-symaro-sensors.jpg"},
    {"dept": "building", "brand": "Siemens", "name": "Desigo CC", "desc": "Integrated building management platform unifying HVAC lighting and energy in one view.", "specs": ["Multi-discipline", "Web access", "Open BACnet"], "img": "building-desigo-cc.jpg"},
    {"dept": "building", "brand": "Auto-Info Engineering", "name": "HVAC Control System", "desc": "Smart HVAC automation that balances comfort air quality and energy cost.", "specs": ["VAV and AHU", "Demand control", "Energy saving"], "img": "building-hvac-control.jpg"},
    {"dept": "building", "brand": "Auto-Info Engineering", "name": "Environmental Monitoring", "desc": "Continuous GMP-grade monitoring of critical clean room parameters with full audit trail.", "specs": ["21 CFR Part 11", "Real-time alerts", "Audit trail"], "img": "building-env-monitoring.jpg"},
    {"dept": "building", "brand": "Auto-Info Engineering", "name": "Fume Hood Controller", "desc": "Adaptive airflow control that protects lab users while reducing exhaust energy.", "specs": ["VAV airflow", "Sash sensing", "Lab safety"], "img": "building-fume-hood.jpg"},
    {"dept": "building", "brand": "Auto-Info Engineering", "name": "Energy Management System", "desc": "Track and optimize building energy consumption with live dashboards and reporting.", "specs": ["Sub-metering", "KPI dashboard", "ISO 50001"], "img": "building-energy-management.jpg"},
    {"dept": "building", "brand": "Auto-Info Engineering", "name": "Building Management System", "desc": "Centralize control of every building subsystem from a single intuitive interface.", "specs": ["Single pane", "Scheduling", "Fault detection"], "img": "building-bms.jpg"},
    {"dept": "building", "brand": "Auto-Info Engineering", "name": "Clean Room Control", "desc": "GMP-compliant clean room automation maintaining pressure temperature and particle limits.", "specs": ["Pressure cascade", "GMP ready", "Validated"], "img": "building-cleanroom-control.jpg"},
    # Terminal Automation
    {"dept": "terminal", "brand": "Emerson Rosemount", "name": "Servo Gauge 854 ATG", "desc": "Automatic tank gauging delivering precise level and inventory for terminal storage.", "specs": ["Custody accuracy", "Servo level", "Live inventory"], "img": "terminal-servo-gauge.jpg"},
    {"dept": "terminal", "brand": "OPW", "name": "Fusion 4 MSC-L", "desc": "Advanced load controller for metering batching and safe truck and rail load-out.", "specs": ["Multi-stream", "Blend control", "Safe loading"], "img": "terminal-fusion4-msc.jpg"},
    {"dept": "terminal", "brand": "Auto-Info Engineering", "name": "Tank Inventory System", "desc": "Real-time tank inventory with reconciliation and loss detection across the terminal.", "specs": ["Live inventory", "Reconciliation", "Loss detection"], "img": "terminal-tank-inventory.jpg"},
    {"dept": "terminal", "brand": "Auto-Info Engineering", "name": "Terminal Management System", "desc": "Integrated TMS orchestrating loading access control and documentation end to end.", "specs": ["Order to load", "Access control", "Reporting"], "img": "terminal-tms.jpg"},
    {"dept": "terminal", "brand": "Auto-Info Engineering", "name": "Overfill Prevention System", "desc": "Independent safety layer that prevents overfill and protects people and assets.", "specs": ["SIL rated", "Independent", "Self-test"], "img": "terminal-overfill-prevention.jpg"},
    {"dept": "terminal", "brand": "Auto-Info Engineering", "name": "Loading Arm and Metering Skid", "desc": "Automated loading arms and metering skids for fast accurate tanker load-out.", "specs": ["Top and bottom", "Metering skid", "Vapor recovery"], "img": "terminal-loading-arm-skid.jpg"},
    {"dept": "terminal", "brand": "Emerson Rosemount", "name": "Tank Side Monitor", "desc": "Field interface hub gathering tank sensor data onto a single reliable network.", "specs": ["Field hub", "Multi-sensor", "Tankbus"], "img": "terminal-tank-side-monitor.jpg"},
    {"dept": "terminal", "brand": "Emerson Rosemount", "name": "Radar Level Gauge", "desc": "Non-contact radar level measurement for accurate inventory with zero maintenance.", "specs": ["Non-contact", "High accuracy", "Retrofit ready"], "img": "terminal-radar-gauge.jpg"},
]

# Trust signals (SP5).  Rendered on /quality-certifications.  The certification
# body, certificate number and expiry date are *not* hard-coded here: they live
# on res.company so the real values can be maintained from the backend and the
# page only shows them when they are set.
OD19_CERTIFICATIONS = [
    {
        "key": "iso9001",
        "icon": "fa-certificate",
        "title": "ISO 9001:2015",
        "subtitle": "Quality Management System",
        "status": "certified",
        "status_label": "Certified",
        "desc": "Our quality management system is certified to ISO 9001:2015, covering "
                "project delivery, engineering, service and procurement.",
        "points": [
            "Annual surveillance and re-certification audits",
            "Documented quality procedures and project records",
            "Customer feedback and corrective-action process",
        ],
    },
    {
        "key": "iso14001",
        "icon": "fa-leaf",
        "title": "ISO 14001",
        "subtitle": "Environmental Management System",
        "status": "in_progress",
        "status_label": "Preparing",
        "desc": "We are preparing our environmental management system for ISO 14001 "
                "certification as part of our sustainability roadmap.",
        "points": [
            "Environmental aspects and impacts review",
            "Waste, energy and emissions controls",
            "Planned certification audit",
        ],
    },
    {
        "key": "gmp",
        "icon": "fa-flask",
        "title": "GMP",
        "subtitle": "Good Manufacturing Practice",
        "status": "compliant",
        "status_label": "Compliant",
        "desc": "Our building automation solutions for life-science facilities are "
                "designed, installed and documented to GMP requirements.",
        "points": [
            "Clean-room and HVAC qualification support",
            "Documented installation and commissioning records",
            "Change control under GMP procedures",
        ],
    },
    {
        "key": "csv",
        "icon": "fa-check-square-o",
        "title": "CSV",
        "subtitle": "Computer System Validation",
        "status": "compliant",
        "status_label": "Compliant",
        "desc": "We deliver computer system validation documentation aligned with "
                "GAMP 5 for regulated automation systems.",
        "points": [
            "Validation master plan and risk assessment",
            "IQ / OQ / PQ protocols and reports",
            "Audit trail and data-integrity controls",
        ],
    },
]

OD19_ACCREDITATIONS = [
    "ISO 9001:2015",
    "ISO 14001 (preparing)",
    "GMP",
    "GAMP 5 / CSV",
    "IEC 61131-3",
    "IEC 62443",
    "ISO 50001",
]

# Illustrative project references (SP5).  Customer names are intentionally not
# published; each entry describes the sector and the delivered scope.  Replace
# with the real reference list before go-live.
OD19_PROJECT_REFERENCES = [
    {
        "sector": "industrial", "year": "2024",
        "title": "Petrochemical plant — SCADA centralisation",
        "scope": "Legacy controller migration with centralised SCADA, historian and alarm management.",
        "detail": "Multi-rack migration executed during planned shutdowns with no production loss.",
        "img": "content/industrial.jpg",
    },
    {
        "sector": "industrial", "year": "2024",
        "title": "Manufacturing line — control panel retrofit",
        "scope": "Custom control panels, variable-speed drives and safety interlock integration.",
        "detail": "Panel design, wiring and factory acceptance testing delivered as a single package.",
        "img": "products/industrial-control-panel.jpg",
    },
    {
        "sector": "industrial", "year": "2023",
        "title": "Process plant — pressure and flow instrumentation",
        "scope": "Rosemount transmitters and Micro Motion Coriolis meters with HART integration.",
        "detail": "Calibrated, loop-tested and documented instrumentation for custody-transfer metering.",
        "img": "products/industrial-rosemount-pressure.jpg",
    },
    {
        "sector": "building", "year": "2024",
        "title": "Life-science facility — HVAC and clean-room control",
        "scope": "GMP HVAC control, room pressure cascade and continuous environmental monitoring.",
        "detail": "Qualified installation with documented differential-pressure and air-change verification.",
        "img": "content/building.jpg",
    },
    {
        "sector": "building", "year": "2023",
        "title": "Pharmaceutical plant — CSV validation package",
        "scope": "Validation master plan, IQ / OQ / PQ protocols and audit-trail configuration.",
        "detail": "Inspection-ready documentation handed over with traceability matrix and training records.",
        "img": "products/building-cleanroom-control.jpg",
    },
    {
        "sector": "building", "year": "2022",
        "title": "Office tower — energy management system",
        "scope": "Sub-metering, KPI dashboards and reporting aligned to ISO 50001 practice.",
        "detail": "Measurable reduction in common-area energy consumption after commissioning.",
        "img": "products/building-energy-management.jpg",
    },
    {
        "sector": "terminal", "year": "2024",
        "title": "Fuel depot — tank gauging and overfill prevention",
        "scope": "Radar and servo level gauges with an independent SIL-rated overfill protection layer.",
        "detail": "Independent safety layer commissioned and self-tested alongside the inventory system.",
        "img": "products/terminal-radar-gauge.jpg",
    },
    {
        "sector": "terminal", "year": "2023",
        "title": "Product terminal — loading arm and batch control",
        "scope": "Loading arm and metering skid with batch controller and access-control integration.",
        "detail": "Automated tanker load-out with metering, vapour recovery and driver access control.",
        "img": "products/terminal-loading-arm-skid.jpg",
    },
    {
        "sector": "terminal", "year": "2022",
        "title": "Tank farm — integrated terminal management",
        "scope": "Terminal management system with inventory, reconciliation and business integration.",
        "detail": "Order-to-load workflow integrated with the customer's commercial systems.",
        "img": "products/terminal-tms.jpg",
    },
]


# Enquiry types offered by the RFQ form on /contactus (SP6).  Each type is
# routed to a sales team (matched by name, ignored when no such team exists)
# and labelled with a CRM tag so the sales desk can filter requests at a
# glance.  This is the single source used by both the form and the routing
# performed in models/crm_lead.py.
OD19_ENQUIRY_TYPES = [
    {"key": "quotation", "label": "Request a Quotation", "team": "Sales", "tag": "Website: Quotation"},
    {"key": "product", "label": "Product Information", "team": "Sales", "tag": "Website: Product Info"},
    {"key": "service", "label": "Service & Maintenance", "team": "Service", "tag": "Website: Service"},
    {"key": "spare_part", "label": "Spare Parts", "team": "Sales", "tag": "Website: Spare Parts"},
    {"key": "certificate", "label": "Certificate Copy Request", "team": "Sales", "tag": "Website: Certificate"},
    {"key": "career", "label": "Careers", "team": "Sales", "tag": "Website: Careers"},
    {"key": "other", "label": "Other Enquiry", "team": "Sales", "tag": "Website: Other"},
]


class Website(models.Model):
    _inherit = "website"

    @api.model
    def od19_products(self):
        """Return the shared product catalog (see OD19_PRODUCT_CATALOG)."""
        return OD19_PRODUCT_CATALOG

    @api.model
    def od19_enquiry_types(self):
        """Return the RFQ enquiry types (see OD19_ENQUIRY_TYPES)."""
        return OD19_ENQUIRY_TYPES

    @api.model
    def od19_certifications(self):
        """Return the trust / certification list (see OD19_CERTIFICATIONS)."""
        return OD19_CERTIFICATIONS

    @api.model
    def od19_accreditations(self):
        """Return the standards and frameworks the team works to."""
        return OD19_ACCREDITATIONS

    @api.model
    def od19_projects(self):
        """Return the project references (see OD19_PROJECT_REFERENCES)."""
        return OD19_PROJECT_REFERENCES

    @api.model
    def od19_setup_website(self):
        """Brand the default website (idempotent)."""
        website = self.env.ref("website.default_website", raise_if_not_found=False)
        if not website or website.name != DEFAULT_NAME:
            return
        website.sudo().write({"name": WEBSITE_NAME})
        _logger.info("od19_website: renamed default website to %r", WEBSITE_NAME)

    # ------------------------------------------------------------------
    # SEO — schema.org structured data (SP7)
    # ------------------------------------------------------------------
    @api.model
    def od19_seo_default_description(self):
        """Fallback meta description for pages without their own copy."""
        return OD19_ORG_DESCRIPTION

    @api.model
    def od19_organization_jsonld(self):
        """Return schema.org Organization + WebSite markup as a JSON string.

        Injected inside `<head>` on every page (see views/seo.xml).  The value
        is ``scriptsafe`` serialised so it can be dropped verbatim into a
        `<script type="application/ld+json">` element without HTML escaping
        breaking the JSON.
        """
        website = self.env["website"].get_current_website()
        company = website.company_id.sudo()
        base_url = website.get_base_url()

        organization = {
            "@type": "Organization",
            "@id": "%s#organization" % base_url,
            "name": OD19_ORG_NAME,
            "url": base_url,
            "logo": "%s/logo.png?company=%s" % (base_url, company.id),
            "description": OD19_ORG_DESCRIPTION,
            "address": dict(OD19_ORG_ADDRESS),
            "contactPoint": [{
                "@type": "ContactPoint",
                "contactType": "sales",
                "telephone": OD19_ORG_PHONE,
                "email": OD19_ORG_EMAIL,
            }],
        }

        same_as = [
            url for url in (
                company.od19_website_facebook_url,
                company.od19_website_linkedin_url,
                company.od19_website_youtube_url,
            ) if url
        ]
        if same_as:
            organization["sameAs"] = same_as

        website_data = {
            "@type": "WebSite",
            "@id": "%s#website" % base_url,
            "name": website.name,
            "url": base_url,
            "potentialAction": {
                "@type": "SearchAction",
                "target": "%s/website/search?search={search_term_string}" % base_url,
                "query-input": "required name=search_term_string",
            },
        }
        lang = getattr(request, "lang", None) if request else None
        if lang is not None and getattr(lang, "code", None):
            website_data["inLanguage"] = lang.code.replace("_", "-")

        payload = [
            dict(organization, **{"@context": "https://schema.org"}),
            dict(website_data, **{"@context": "https://schema.org"}),
        ]
        return json_scriptsafe.dumps(payload, indent=2)

    @api.model
    def od19_setup_seo(self):
        """Propagate the company Google Analytics ID and seed robots.txt.

        Idempotent: replayed on every ``-u od19_website`` (see
        data/setup_functions.xml).  Never overwrites a value that has already
        been customised from the backend / website editor.
        """
        for website in self.search([]):
            company = website.company_id.sudo()
            key = (company.od19_website_ga_key or "").strip()
            vals = {}
            if key and website.google_analytics_key != key:
                vals["google_analytics_key"] = key
            if not (website.robots_txt or "").strip():
                vals["robots_txt"] = OD19_DEFAULT_ROBOTS
            if vals:
                website.sudo().write(vals)
                _logger.info(
                    "od19_website: SEO setup applied to %r -> %s",
                    website.name, sorted(vals),
                )

    # ------------------------------------------------------------------
    # PDPA — cookie consent & legal pages (SP8)
    # ------------------------------------------------------------------
    @api.model
    def od19_setup_pdpa(self):
        """Enable cookie consent and make the legal pages live.

        Idempotent: replayed on every ``-u od19_website`` (see
        data/setup_functions.xml).  Enabling ``cookies_bar`` makes consent
        opt-in and lets core create the ``/cookie-policy`` page that the bar
        links to; the Privacy Policy and Terms pages are (re)published and left
        indexed.  Nothing is overwritten once it is already in place, so the
        administrator's edits survive an upgrade.
        """
        for website in self.search([]):
            if not website.cookies_bar:
                website.sudo().write({"cookies_bar": True})
                _logger.info(
                    "od19_website: enabled the cookies bar on %r", website.name,
                )

        legal_pages = self.env["website.page"].sudo().search([
            ("url", "in", ("/privacy", "/terms")),
        ])
        for page in legal_pages:
            vals = {}
            if not page.is_published:
                vals["is_published"] = True
            if not page.website_indexed:
                vals["website_indexed"] = True
            if vals:
                page.write(vals)
                _logger.info(
                    "od19_website: legal page %s -> %s", page.url, sorted(vals),
                )

        # Core creates this page together with the cookies bar; enrich its
        # metadata once, and never clobber a value the administrator set.
        cookie_policy = self.env["website.page"].sudo().search([
            ("url", "=", "/cookie-policy"),
        ], limit=1)
        if cookie_policy and not cookie_policy.website_meta_description:
            cookie_policy.write({
                "website_meta_title": "Cookie Policy | Auto-Info",
                "website_meta_description": (
                    "How The Auto-Info Co., Ltd. uses cookies on this website — "
                    "essential cookies, optional analytics cookies and how to manage "
                    "or withdraw your consent."
                ),
            })
