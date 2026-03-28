# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged
from odoo.addons.website.tests.test_configurator import TestConfiguratorCommon


# TODO: `test_themes` tag should not be there, runbot config should be adapted
#       to test this module too. There is a special config for the theme repo.
@tagged('post_install', '-at_install', 'test_themes')
class Crawler(HttpCase):
    def test_01_menu_hierarchies(self):
        theme_custo = self.env.ref('base.module_theme_test_custo')
        website = self.env['website'].browse(1)
        website.theme_id = theme_custo.id
        theme_custo.with_context(load_all_views=True, apply_new_theme=True)._theme_load(website)
        self.start_tour('/@/example', "theme_menu_hierarchies", login='admin')

