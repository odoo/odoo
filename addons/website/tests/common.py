# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import HttpCase


class HttpCaseWithUserRestricted(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_restricted = cls.env["res.users"].search([("login", "=", "restricted")])
        cls.partner_restricted = cls.user_restricted.partner_id

        if not cls.user_restricted:
            cls.env["ir.config_parameter"].sudo().set_param("auth_password_policy.minlength", 4)
            cls.partner_restricted = cls.env["res.partner"].create({
                "name": "Rafe Restricted",
                "email": "rafe.cameron23@example.com",
            })
            cls.user_restricted = cls.env["res.users"].create({
                "login": "restricted",
                "password": "restricted",
                "partner_id": cls.partner_restricted.id,
                "groups_id": [Command.set([cls.env.ref("base.group_user").id, cls.env.ref("website.group_website_restricted_editor").id])],
            })
