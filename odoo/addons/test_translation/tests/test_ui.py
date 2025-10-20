import odoo.tests
from odoo.tools import mute_logger


@odoo.tests.tagged('-at_install', 'post_install')
class TestUiTranslation(odoo.tests.HttpCase):

    @mute_logger('odoo.sql_db', 'odoo.http')
    def test_01_sql_constraints(self):
        # Raise an SQL constraint and test the message
        self.env['res.lang']._activate_lang('fr_FR')
        self.env.ref('base.module_test_translation')._update_translations(['fr_FR'])
        constraint = self.env.ref('test_translation.constraint_test_translation_constraint_positive_code')
        message = constraint.with_context(lang='fr_FR').message
        self.assertEqual(message, "Le code doit être une valeur positive !")

        # TODO: make the test work with French translations. As the transaction
        # is rollbacked at insert and a new cursor is opened, can not test that
        # the message is translated (_load_module_terms is also) rollbacked.
        # Test individually the external id and loading of translation.
        self.start_tour("/odoo/action-test_translation.action_constraint", 'sql_constraint', login="admin")
