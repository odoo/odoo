# copyright 2020 Camptocamp
# license lgpl-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import exceptions
from odoo.tests import common


class TestJobWriteProtected(common.TransactionCase):
    def test_create_error(self):
        with self.assertRaises(exceptions.AccessError):
            self.env["queue.job"].create(
                {"uuid": "test", "model_name": "res.partner", "method_name": "write"}
            )

    def test_write_protected_field_error(self):
        job_ = self.env["res.partner"].with_delay().create({"name": "test"})
        db_job = job_.db_record()
        with self.assertRaises(exceptions.AccessError):
            db_job.method_name = "unlink"

    def test_write_allow_no_protected_field_error(self):
        job_ = self.env["res.partner"].with_delay().create({"name": "test"})
        db_job = job_.db_record()
        db_job.priority = 30
        self.assertEqual(db_job.priority, 30)
