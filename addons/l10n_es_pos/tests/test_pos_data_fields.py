from odoo.tests import TransactionCase, tagged


@tagged("post_install", "post_install_l10n", "-at_install")
class TestPosClientFields(TransactionCase):
    READ_BY_THE_CLIENT = ("is_spanish", "simplified_partner_id")

    def test_the_computed_flags_still_reach_the_browser(self):
        config = self.env["pos.config"]
        sent = set(config._load_pos_data_fields(config.browse()))
        missing = [name for name in self.READ_BY_THE_CLIENT if name not in sent]
        self.assertFalse(
            missing,
            "these fields are read by the POS client but are no longer sent to "
            "it; declare them in _get_pos_client_computed_fields: %s" % missing,
        )

    def test_the_flags_are_still_the_computed_ones_this_module_installs(self):
        """If a field goes back to being stored the test above passes for a
        different reason, so pin why the declaration is needed at all."""
        for name in self.READ_BY_THE_CLIENT:
            field = self.env["pos.config"]._fields[name]
            self.assertTrue(
                field.compute and not field.store,
                f"{name} is no longer a non-stored computed field, so this "
                "module's declaration of it may now be unnecessary",
            )
