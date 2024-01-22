# Copyright 2019 Alexandre Díaz <dev@redneboa.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import common

from ..models.res_company import URL_BASE


class TestResCompany(common.TransactionCase):
    IMG_GREEN = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUl"
        + "EQVR42mNk+M/wHwAEBgIApD5fRAAAAABJRU5ErkJggg=="
    )

    def _test_scss_attachment(self):
        num_scss = self.env["ir.attachment"].search_count(
            [("url", "ilike", "%s%%" % URL_BASE)]
        )
        num_companies = self.env["res.company"].search_count([])
        self.assertEqual(num_scss, num_companies, "Invalid scss attachments")

    def test_create_unlink_company(self):
        company_id = self.env["res.company"].create({"name": "Company Test"})
        self.assertEqual(
            company_id.color_navbar_bg, False, "Invalid Navbar Background Color"
        )
        self._test_scss_attachment()
        company_id.sudo().write({"logo": self.IMG_GREEN})
        company_id.button_compute_color()
        self.assertEqual(
            company_id.color_navbar_bg, "#00ff00", "Invalid Navbar Background Color"
        )
        # TODO: We can't remove companies if they have attached data, like
        # warehouse when we have stock module installed
        # company_id.sudo().unlink()
        # self._test_scss_attachment()

    def test_change_logo(self):
        company_id = self.env["res.company"].search([], limit=1)
        company_id.sudo().write({"logo": self.IMG_GREEN})
        company_id.button_compute_color()
        self.assertEqual(
            company_id.color_navbar_bg, "#00ff00", "Invalid Navbar Background Color"
        )

    def test_scss_sanitized_values(self):
        company_id = self.env["res.company"].search([], limit=1)
        company_id.sudo().write({"color_navbar_bg": False})
        values = company_id.sudo()._scss_get_sanitized_values()
        self.assertEqual(
            values["color_navbar_bg"],
            "$o-brand-odoo",
            "Invalid Navbar Background Color",
        )
        company_id.sudo().write({"color_navbar_bg": "#DEAD00"})
        values = company_id.sudo()._scss_get_sanitized_values()
        self.assertEqual(
            values["color_navbar_bg"], "#DEAD00", "Invalid Navbar Background Color"
        )

    def test_change_color(self):
        company_id = self.env["res.company"].search([], limit=1)
        company_id.sudo().write({"color_navbar_bg": "#DEAD00"})
        self.assertEqual(
            company_id.color_navbar_bg, "#DEAD00", "Invalid Navbar Background Color"
        )
        self.assertEqual(
            company_id.company_colors["color_navbar_bg"],
            "#DEAD00",
            "Invalid Navbar Background Color",
        )
        company_id.sudo().write({"color_navbar_bg": False})
        self.assertFalse(company_id.color_navbar_bg, "Invalid Navbar Background Color")
        self.assertNotIn(
            "color_navbar_bg",
            company_id.company_colors,
            "Invalid Navbar Background Color",
        )
