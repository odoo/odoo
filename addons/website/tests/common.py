# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlsplit

from lxml import html

from odoo.fields import Command
from odoo.tests import HttpCase


def all_sitemap_urls(case):
    """Return the concatenated body of every sub-sitemap listed in /sitemap.xml.

    /sitemap.xml is a sitemap index; the actual URLs live in per-section
    sub-sitemaps it links to. Section names depend on which modules are installed
    (a controller override changes the owning module, e.g. 'sale' -> 'sale-renting'),
    so tests should search the union of all sub-sitemaps.
    """
    index = html.fromstring(case.url_open('/sitemap.xml').content)
    return '\n'.join(
        case.url_open(urlsplit(loc).path).text
        for loc in index.xpath('//loc/text()')
    )


class HttpCaseWithWebsiteUser(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.ref("base.main_company")
        country = cls.env.ref("base.us")
        state = cls.env["res.country.state"].search([("code", "=", "NY")], limit=1)
        partner_vals = {
            "name": "Rafe Restricted",
            "company_id": company.id,
            "street": "725 5th Ave",
            "city": "New York",
            "state_id": state.id if state else False,
            "zip": "10022",
            "country_id": country.id,
            "tz": "America/New_York",
            "email": "rafe.cameron23@example.com",
            "phone": "+1(492)-563-3759",
        }
        cls.partner_website_user = cls.env["res.partner"].create(partner_vals)
        cls.user_website_user = cls.env["res.users"].create({
            "partner_id": cls.partner_website_user.id,
            "login": "website_user",
            "password": "website_user",
            "signature": "<span>-- <br/>+Mr Restricted</span>",
            "company_id": company.id,
            "image_1920": cls.file_read("website/static/src/img/user-restricted-image.png"),
            "group_ids": [
                Command.unlink(cls.env.ref("website.group_website_designer").id),
                Command.link(cls.env.ref("website.group_website_restricted_editor").id),
                Command.link(cls.env.ref("base.group_user").id),
            ],
        })
