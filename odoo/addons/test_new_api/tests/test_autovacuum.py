# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo.tests import common


class TestAutovacuum(common.TransactionCase):

    def test_api_autovacuum(self):
        Model = self.env['test_new_api.autovacuumed']
        instance = Model.create({'expire_at': datetime.now() - timedelta(days=15)})
        self.assertTrue(instance.exists())

        self.env.ref('base.autovacuum_job').method_direct_trigger()

        self.assertFalse(instance.exists())
