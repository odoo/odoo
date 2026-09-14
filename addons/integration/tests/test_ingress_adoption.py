from odoo.tests import TransactionCase, tagged

from ..tools.ingress_adoption import adopt_ingress_from_credential

_PROBES = (
    "model_inbound_access_log",
    "model_mixin_inbound_gate",
    "field_inbound_access_log__outcome",
    "field_mixin_inbound_gate__signature_header",
    "action_inbound_access_log",
    "ir_cron_gc_inbound_access_logs",
)


@tagged("post_install", "-at_install")
class TestIngressAdoption(TransactionCase):
    def _owners(self):
        self.env.cr.execute(
            "SELECT name, module FROM ir_model_data WHERE name = ANY(%s)",
            (list(_PROBES),),
        )
        return dict(self.env.cr.fetchall())

    def test_nothing_is_adopted_when_credential_never_owned_the_gate(self):
        self.assertEqual(adopt_ingress_from_credential(self.env.cr), 0)

    def test_the_gate_and_its_log_change_owner_instead_of_being_deleted(self):
        self.env.cr.execute(
            """
            UPDATE ir_model_data SET module = 'credential'
             WHERE module = 'integration'
               AND (
                   name LIKE ANY(%s)
                   OR name IN (
                       'model_inbound_access_log', 'model_mixin_inbound_gate',
                       'action_inbound_access_log', 'menu_inbound_access_logs',
                       'view_inbound_access_log_list', 'view_inbound_access_log_search',
                       'ir_cron_gc_inbound_access_logs',
                       'ir_cron_gc_inbound_access_logs_ir_actions_server',
                       'access_inbound_access_log_user', 'access_inbound_access_log_admin'
                   )
               )
            """,
            (["field_inbound_access_log__%", "field_mixin_inbound_gate__%"],),
        )
        handed_back = self.env.cr.rowcount
        self.env.cr.execute(
            """
            UPDATE ir_model_constraint
               SET module = (SELECT id FROM ir_module_module WHERE name = 'credential')
             WHERE model = (SELECT id FROM ir_model WHERE model = 'inbound.access.log')
            """
        )

        adopted = adopt_ingress_from_credential(self.env.cr)

        self.assertEqual(adopted, handed_back)
        self.assertEqual(set(self._owners().values()), {"integration"})
        self.env.cr.execute(
            """
            SELECT DISTINCT m.name FROM ir_model_constraint c
              JOIN ir_module_module m ON m.id = c.module
             WHERE c.model = (SELECT id FROM ir_model WHERE model = 'inbound.access.log')
            """
        )
        self.assertEqual(self.env.cr.fetchall(), [("integration",)])
