from odoo.tests import TransactionCase, tagged

from ..hooks import adopt_from_automation

_PROBES = (
    "field_automation_rule__webhook_uuid",
    "field_automation_rule__signature_header",
    "field_automation_rule__credential_id",
    "selection__automation_rule__trigger__on_webhook",
)


@tagged("post_install", "-at_install")
class TestAdoptionFromAutomation(TransactionCase):
    def _owners(self):
        self.env.cr.execute(
            "SELECT name, module FROM ir_model_data WHERE name = ANY(%s)",
            (list(_PROBES),),
        )
        return dict(self.env.cr.fetchall())

    def test_nothing_is_adopted_when_automation_never_owned_the_webhook(self):
        self.assertEqual(adopt_from_automation(self.env), 0)

    def test_automation_records_change_owner_instead_of_being_deleted(self):
        self.env.cr.execute(
            """
            UPDATE ir_model_data SET module = 'automation'
             WHERE module = 'automation_webhook' AND name = ANY(%s)
            """,
            (list(_PROBES),),
        )

        adopted = adopt_from_automation(self.env)

        self.assertEqual(adopted, len(_PROBES))
        self.assertEqual(set(self._owners().values()), {"automation_webhook"})

    def test_every_webhook_record_automation_could_have_owned_is_adopted(self):
        self.env.cr.execute(
            """
            UPDATE ir_model_data SET module = 'automation'
             WHERE module = 'automation_webhook'
               AND name LIKE ANY(%s)
               AND name != ALL(%s)
               AND NOT EXISTS (
                   SELECT 1 FROM ir_model_data own
                    WHERE own.module = 'automation' AND own.name = ir_model_data.name
               )
            """,
            (
                [
                    "field_automation_rule__%",
                    "selection__automation_rule__trigger__%",
                    "model_inherit__automation_rule__%",
                ],
                ["field_automation_rule__webhook_enforce_from"],
            ),
        )
        moved = self.env.cr.rowcount

        self.assertGreater(moved, len(_PROBES))
        self.assertEqual(adopt_from_automation(self.env), moved)
