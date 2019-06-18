# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_create_and_edit_note(self):
        self.phantom_js("/web", "odoo.__DEBUG__.services['web_tour.tour'].run('note_tour')", "odoo.__DEBUG__.services['web_tour.tour'].tours.note_tour.ready", login="admin")
