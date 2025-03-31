from datetime import datetime, timedelta

from odoo.tests import common


class TestAutovacuum(common.TransactionCase):
    def test_api_autovacuum(self):
        Model = self.env['test_orm.autovacuumed']
        instance = Model.create({'expire_at': datetime.now() - timedelta(days=15)})
        self.assertTrue(instance.exists())

        # Run the autovacuum cron
        with self.enter_registry_test_mode():
            self.env.ref('base.autovacuum_job').method_direct_trigger()

        # Check the record has been vacuumed.
        self.assertFalse(instance.exists())
