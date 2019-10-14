# coding: utf-8
from odoo.tests import common


class TestTheme(common.TransactionCase):

    def test_theme_remove_working(self):
        """ This test ensure theme can be removed.
        Theme removal is also the first step during theme installation.
        """
        theme_common_module = self.env['ir.module.module'].search([('name', '=', 'theme_default')])
        website = self.env['website'].get_current_website()
        website.theme_id = theme_common_module.id
        self.env['ir.module.module']._theme_remove(website)
