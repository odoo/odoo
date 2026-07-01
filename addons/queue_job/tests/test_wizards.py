# license lgpl-3.0 or later (http://www.gnu.org/licenses/lgpl.html)
from odoo.tests import common


class TestWizards(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.job = (
            self.env["queue.job"]
            .with_context(
                _job_edit_sentinel=self.env["queue.job"].EDIT_SENTINEL,
            )
            .create(
                {
                    "uuid": "test",
                    "user_id": self.env.user.id,
                    "state": "failed",
                    "model_name": "queue.job",
                    "method_name": "write",
                    "args": (),
                }
            )
        )

    def _wizard(self, model_name):
        return (
            self.env[model_name]
            .with_context(
                active_model=self.job._name,
                active_ids=self.job.ids,
            )
            .create({})
        )

    def test_01_requeue(self):
        wizard = self._wizard("queue.requeue.job")
        wizard.requeue()
        self.assertEqual(self.job.state, "pending")

    def test_02_cancel(self):
        wizard = self._wizard("queue.jobs.to.cancelled")
        wizard.set_cancelled()
        self.assertEqual(self.job.state, "cancelled")

    def test_03_done(self):
        wizard = self._wizard("queue.jobs.to.done")
        wizard.set_done()
        self.assertEqual(self.job.state, "done")
