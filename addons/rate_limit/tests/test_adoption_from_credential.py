from odoo.tests import TransactionCase, tagged

from ..hooks import adopt_from_credential


@tagged("post_install", "-at_install")
class TestAdoptionFromCredential(TransactionCase):
    def _owners(self, *names):
        self.env.cr.execute(
            "SELECT name, module FROM ir_model_data WHERE name = ANY(%s)",
            (list(names),),
        )
        return dict(self.env.cr.fetchall())

    def _hand_back_to_credential(self):
        self.env.cr.execute(
            "UPDATE ir_model_data SET module = 'credential' WHERE module = 'rate_limit'"
        )
        self.env.cr.execute(
            """
            SELECT c.ir_actions_server_id FROM ir_cron c
              JOIN ir_model_data d ON d.res_id = c.id AND d.model = 'ir.cron'
             WHERE d.module = 'credential' AND d.name = 'ir_cron_cleanup_rate_limiter'
            """
        )
        (action_id,) = self.env.cr.fetchone()
        self.env.cr.execute(
            "UPDATE ir_act_server SET model_id = %s, code = %s WHERE id = %s",
            (
                self.env["ir.model"]._get_id("res.partner"),
                "model.cron_cleanup_rate_limiter()",
                action_id,
            ),
        )
        self.env.cr.execute("SELECT id FROM ir_module_module WHERE name = 'credential'")
        if not self.env.cr.fetchone():
            self.env.cr.execute(
                """
                INSERT INTO ir_module_module (name, state, auto_install, application)
                     VALUES ('credential', 'uninstalled', false, false)
                """
            )
        self.env.cr.execute(
            """
            UPDATE ir_model_constraint
               SET module = (SELECT id FROM ir_module_module WHERE name = 'credential')
             WHERE model = (SELECT id FROM ir_model WHERE model = 'rate.limit.bucket')
            """
        )
        return action_id

    def test_nothing_is_adopted_on_a_database_that_never_had_credential_own_it(self):
        self.assertEqual(adopt_from_credential(self.env.cr), 0)

    def test_credential_records_change_owner_instead_of_being_duplicated(self):
        self._hand_back_to_credential()

        adopted = adopt_from_credential(self.env.cr)

        self.assertGreater(adopted, 0)
        owners = self._owners(
            "model_rate_limit_bucket",
            "field_rate_limit_bucket__tokens",
            "view_rate_limit_bucket_form",
            "ir_cron_cleanup_rate_limiter",
        )
        self.assertEqual(set(owners.values()), {"rate_limit"}, owners)
        self.env.cr.execute(
            """
            SELECT m.name FROM ir_model_constraint c
              JOIN ir_module_module m ON m.id = c.module
             WHERE c.name = 'rate_limit_bucket_bucket_key_uniq'
            """
        )
        self.assertEqual(self.env.cr.fetchall(), [("rate_limit",)])

    def test_the_limiter_cleanup_cron_is_repointed_at_the_bucket_model(self):
        action_id = self._hand_back_to_credential()

        adopt_from_credential(self.env.cr)

        self.env.cr.execute(
            "SELECT model_id, code FROM ir_act_server WHERE id = %s", (action_id,)
        )
        model_id, code = self.env.cr.fetchone()
        self.assertEqual(model_id, self.env["ir.model"]._get_id("rate.limit.bucket"))
        self.assertEqual(code, "model.cron_cleanup_caller_rate_limiter()")
