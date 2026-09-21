from odoo.tests import TransactionCase, tagged

from ..tools.ingress_adoption import adopt_ingress_from_credential

_PROBES = (
    "model_mixin_inbound_gate",
    "field_mixin_inbound_gate__signature_header",
    "menu_inbound_access_logs",
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
                       'model_mixin_inbound_gate', 'menu_inbound_access_logs',
                       'model_inherit__mixin_inbound_gate__mixin_credential_auth'
                   )
               )
            """,
            (["field_mixin_inbound_gate__%"],),
        )
        handed_back = self.env.cr.rowcount

        adopted = adopt_ingress_from_credential(self.env.cr)

        self.assertEqual(adopted, handed_back)
        self.assertEqual(set(self._owners().values()), {"integration"})
