# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase


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


def set_url_code(lang, url_code=None):
    """
    Set the URL code of a language, by default the short form of its code.
    Tests use it for the URLs they expect (/fr for French), but another language
    may already hold that code depending on the installed languages. That
    language gets its full code as URL code instead.

    :param lang: the ``res.lang`` record to give the URL code to
    :param url_code: the URL code to assign to lang, short code by default
    """
    lang = lang.sudo()
    url_code = url_code or lang.code.split('_')[0]
    holder = lang.with_context(active_test=False).search([('url_code', '=', url_code), ('id', '!=', lang.id)])
    holder.url_code = holder.code
    lang.url_code = url_code
