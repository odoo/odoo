# copyright 2020 Camptocamp
# license lgpl-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import exceptions
from odoo.tests import common


class TestJobFunction(common.TransactionCase):
    def test_function_name_compute(self):
        function = self.env["queue.job.function"].create(
            {"model_id": self.env.ref("base.model_res_users").id, "method": "read"}
        )
        self.assertEqual(function.name, "<res.users>.read")

    def test_function_name_inverse(self):
        function = self.env["queue.job.function"].create({"name": "<res.users>.read"})
        self.assertEqual(function.model_id.model, "res.users")
        self.assertEqual(function.method, "read")

    def test_function_name_inverse_invalid_regex(self):
        with self.assertRaises(exceptions.UserError):
            self.env["queue.job.function"].create({"name": "<res.users.read"})

    def test_function_name_inverse_model_not_found(self):
        with self.assertRaises(exceptions.UserError):
            self.env["queue.job.function"].create(
                {"name": "<this.model.does.not.exist>.read"}
            )

    def test_function_job_config(self):
        channel = self.env["queue.job.channel"].create(
            {"name": "foo", "parent_id": self.env.ref("queue_job.channel_root").id}
        )
        job_function = self.env["queue.job.function"].create(
            {
                "model_id": self.env.ref("base.model_res_users").id,
                "method": "read",
                "channel_id": channel.id,
                "edit_retry_pattern": "{1: 2, 3: 4}",
                "edit_related_action": (
                    '{"enable": True,'
                    ' "func_name": "related_action_foo",'
                    ' "kwargs": {"b": 1}}'
                ),
            }
        )
        self.assertEqual(
            self.env["queue.job.function"].job_config("<res.users>.read"),
            self.env["queue.job.function"].JobConfig(
                channel="root.foo",
                retry_pattern={1: 2, 3: 4},
                related_action_enable=True,
                related_action_func_name="related_action_foo",
                related_action_kwargs={"b": 1},
                job_function_id=job_function.id,
            ),
        )
