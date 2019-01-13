# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
import odoo.tests

class TestUiTranslate(odoo.tests.HttpCase):
    def test_admin_tour_rte_translator(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('rte_translator')", "odoo.__DEBUG__.services['web_tour.tour'].tours.rte_translator.ready", login='admin', timeout=120)


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_public_homepage(self):
        self.phantom_js("/", "console.log('ok')", "'website.content.snippets.animation' in odoo.__DEBUG__.services")

    def test_02_admin_tour_banner(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('banner')", "odoo.__DEBUG__.services['web_tour.tour'].tours.banner.ready", login='admin')
