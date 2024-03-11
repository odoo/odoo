# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo.tests import common


class TestAutovacuum(common.TransactionCase):
    def test_api_autovacuum(self):
        Model = self.env['test_new_api.autovacuumed']
        instance = Model.create({'expire_at': datetime.now() - timedelta(days=15)})
        self.assertTrue(instance.exists())

        # Enter test mode to run the autovacuum cron because `_run_vacuum_cleaner` makes a commit
        self.registry.enter_test_mode(self.cr)
        self.addCleanup(self.registry.leave_test_mode)
        env = self.env(cr=self.registry.cursor())

        # Run the autovacuum cron
        env.ref('base.autovacuum_job').method_direct_trigger()

        # Check the record has been vacuumed.
        self.assertFalse(instance.exists())
