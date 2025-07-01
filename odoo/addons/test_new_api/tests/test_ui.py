# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.tools import mute_logger
from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUi(HttpCaseWithUserDemo):

    def test_01_admin_widget_x2many(self):
        # FIXME: breaks if too many children of base.menu_tests

        # This tour turns out to be quite sensible to the number of items in
        # the base.menu_tests: it's specifically sequenced to be lower (after)
        # the default, but doesn't account for the fact that it could
        # "fall off" into the "o_extra_menu_items" section if the window is
        # too small or there are too many items preceding it in the tests menu
        self.start_tour("/odoo/action-test_new_api.action_discussions",
            'widget_x2many', login="admin", timeout=120)


@odoo.tests.tagged('-at_install', 'post_install')
class TestUiTranslation(odoo.tests.HttpCase):

    @mute_logger('odoo.sql_db', 'odoo.http')
    def test_01_sql_constraints(self):
        # Raise an SQL constraint and test the message
        self.env['res.lang']._activate_lang('fr_FR')
        self.env.ref('base.module_test_new_api')._update_translations(['fr_FR'])
        constraint = self.env.ref('test_new_api.constraint_test_new_api_category_positive_color')
        message = constraint.with_context(lang='fr_FR').message
        self.assertEqual(message, "La couleur doit être une valeur positive !")

        # TODO: make the test work with French translations. As the transaction
        # is rollbacked at insert and a new cursor is opened, can not test that
        # the message is translated (_load_module_terms is also) rollbacked.
        # Test individually the external id and loading of translation.
        self.start_tour("/odoo/action-test_new_api.action_categories",
            'sql_constaint', login="admin")
