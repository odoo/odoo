from odoo.tests import TransactionCase, tagged


@tagged("post_install", "post_install_l10n", "-at_install")
class TestPosClientFields(TransactionCase):
    READ_BY_THE_CLIENT = ("is_spanish", "simplified_partner_id")
    WRITTEN_BY_THE_CLIENT = ("is_l10n_es_simplified_invoice",)

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

    def test_the_order_flag_the_client_sets_survives_the_round_trip(self):
        """`askBeforeValidation` sets this on the client and
        `_prepare_invoice_vals` reads it back on the server. A field missing from
        the order payload makes that trip silently: the server's copy stays False
        and the invoice lands in the wrong journal while the receipt still says
        the order was simplified."""
        order = self.env["pos.order"]
        sent = set(order._load_pos_data_fields(self.env["pos.config"].browse()))
        missing = [name for name in self.WRITTEN_BY_THE_CLIENT if name not in sent]
        self.assertFalse(
            missing,
            "the POS client writes these and the server reads them back, but they "
            "are not in the order payload: %s" % missing,
        )
