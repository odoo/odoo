from odoo import api
from odoo.tests import TransactionCase


class PopulateTestCase(TransactionCase):
    """
    Use a TestCursor because start_populate() commits during job execution or on retrying.
    """

    def setUp(self):
        super().setUp()
        self.enterContext(self.enter_registry_test_mode())
        self.cr = self.registry.cursor()
        self.addCleanup(self.cr.close)
        self.env = api.Environment(self.cr, api.SUPERUSER_ID, {})
