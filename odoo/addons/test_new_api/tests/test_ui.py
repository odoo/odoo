import odoo.tests
from odoo.tools import mute_logger


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_admin_widget_x2many(self):
        # FIXME: breaks if too many children of base.menu_tests

        # This tour turns out to be quite sensible to the number of items in
        # the base.menu_tests: it's specifically sequenced to be lower (after)
        # the default, but doesn't account for the fact that it could
        # "fall off" into the "o_extra_menu_items" section if the window is
        # too small or there are too many items preceding it in the tests menu
        self.start_tour("/web#action=test_new_api.action_discussions",
            'widget_x2many', step_delay=100, login="admin", timeout=120)


class TestUiTranslation(odoo.tests.HttpCase):

    @mute_logger('odoo.sql_db', 'odoo.http')
    def test_01_sql_constraints(self):
        # Raise an SQL constraint and test the message
        self.env['ir.translation']._load_module_terms(['test_new_api'], ['fr_FR'])
        constraint = self.env.ref('test_new_api.constraint_test_new_api_category_positive_color')
        message = constraint.with_context(lang='fr_FR').message
        self.assertEqual(message, "La couleur doit être une valeur positive !")

        # TODO: make the test work with French translations. As the transaction
        # is rollbacked at insert and a new cusor is opened, can not test that
        # the message is translated (_load_module_terms is also) rollbacked.
        # Test individually the external id and loading of translation.
        self.start_tour("/web#action=test_new_api.action_categories",
            'sql_constaint', login="admin")
