# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo.fields import Command
from odoo.tests import HttpCase
from odoo.tools import file_open


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
            "company_name": "YourCompany",
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
            "image_1920": base64.b64encode(file_open("website/static/src/img/user-restricted-image.png", "rb").read()),
            "group_ids": [
                Command.unlink(cls.env.ref("website.group_website_designer").id),
                Command.link(cls.env.ref("website.group_website_restricted_editor").id),
                Command.link(cls.env.ref("base.group_user").id),
            ],
        })
