# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
import odoo.tests


class TestUi(odoo.tests.HttpCase):

    def test_01_public_homepage(self):
        self.phantom_js("/", "console.log('ok')", "'website.snippets.animation' in odoo.__DEBUG__.services")

    def test_02_admin_homepage(self):
        self.phantom_js("/", "console.log('ok')", "'website.snippets.editor' in odoo.__DEBUG__.services", login='admin')

    def test_03_admin_tour_banner(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('banner')", "odoo.__DEBUG__.services['web_tour.tour'].tours.banner", login='admin')

    def test_03_admin_tour_rte_translator(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('rte_translator', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.rte_translator", login='admin')
