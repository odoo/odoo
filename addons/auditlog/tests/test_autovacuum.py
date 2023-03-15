# Copyright 2016 ABF OSIELL <https://osiell.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import time

from odoo.tests.common import TransactionCase


class TestAuditlogAutovacuum(TransactionCase):
    def setUp(self):
        super(TestAuditlogAutovacuum, self).setUp()
        self.groups_model_id = self.env.ref("base.model_res_groups").id
        self.groups_rule = self.env["auditlog.rule"].create(
            {
                "name": "testrule for groups",
                "model_id": self.groups_model_id,
                "log_read": True,
                "log_create": True,
                "log_write": True,
                "log_unlink": True,
                "state": "subscribed",
                "log_type": "full",
            }
        )

    def tearDown(self):
        self.groups_rule.unlink()
        super(TestAuditlogAutovacuum, self).tearDown()

    def test_autovacuum(self):
        log_model = self.env["auditlog.log"]
        autovacuum_model = self.env["auditlog.autovacuum"]
        group = self.env["res.groups"].create({"name": "testgroup1"})
        nb_logs = log_model.search_count(
            [("model_id", "=", self.groups_model_id), ("res_id", "=", group.id)]
        )
        self.assertGreater(nb_logs, 0)
        # Milliseconds are ignored by autovacuum, waiting 1s ensure that
        # the logs generated will be processed by the vacuum
        time.sleep(1)
        autovacuum_model.autovacuum(days=0)
        nb_logs = log_model.search_count(
            [("model_id", "=", self.groups_model_id), ("res_id", "=", group.id)]
        )
        self.assertEqual(nb_logs, 0)
