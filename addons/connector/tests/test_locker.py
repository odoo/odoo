# Copyright 2018 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from unittest import mock

from odoo import api
from odoo.modules.registry import Registry
from odoo.tests import common

from odoo.addons.component.core import WorkContext
from odoo.addons.component.tests.common import TransactionComponentRegistryCase
from odoo.addons.queue_job.exception import RetryableJobError


class TestLocker(TransactionComponentRegistryCase):
    def setUp(self):
        super().setUp()
        self.backend = mock.MagicMock(name="backend")
        self.backend.env = self.env

        self.registry2 = Registry(common.get_db_name())
        self.cr2 = self.registry2.cursor()
        self.env2 = api.Environment(self.cr2, self.env.uid, {})
        self.backend2 = mock.MagicMock(name="backend2")
        self.backend2.env = self.env2

        @self.addCleanup
        def reset_cr2():
            # rollback and close the cursor, and reset the environments
            self.env2.reset()
            self.cr2.rollback()
            self.cr2.close()

    def test_lock(self):
        """Lock a record"""
        main_partner = self.env.ref("base.main_partner")
        work = WorkContext(model_name="res.partner", collection=self.backend)
        work.component("record.locker").lock(main_partner)

        main_partner2 = self.env2.ref("base.main_partner")
        work2 = WorkContext(model_name="res.partner", collection=self.backend2)
        locker2 = work2.component("record.locker")
        with self.assertRaises(RetryableJobError):
            locker2.lock(main_partner2)
