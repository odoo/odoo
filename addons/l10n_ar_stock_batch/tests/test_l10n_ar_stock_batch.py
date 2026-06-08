from odoo.tests import tagged

from odoo.addons.l10n_ar_stock.tests.test_l10n_ar_delivery_guide import (
    TestArDeliveryGuide,
)


@tagged("post_install_l10n", "post_install", "-at_install")
class TestArStockBatch(TestArDeliveryGuide):
    """Tests for the l10n_ar_stock_batch bridge module."""

    def _create_batch_with_pickings(self, count=2, validate=True):
        """Create pickings inside a batch. Pickings must be added before
        validation because the batch sanity check forbids done pickings."""
        vals = self._get_stock_picking_vals()
        pickings = self.env["stock.picking"].create([dict(vals) for _ in range(count)])
        pickings.action_confirm()

        batch = self.env["stock.picking.batch"].create(
            {
                "picking_type_id": self.picking_type.id,
                "picking_ids": [(4, p.id) for p in pickings],
            },
        )
        if validate:
            pickings.button_validate()
        return batch, pickings

    # --- Computed button visibility --- #

    def test_show_generate_button_on_done_batch(self):
        """Done batch with eligible pickings shows the generate button."""
        batch, _ = self._create_batch_with_pickings()

        self.assertTrue(batch.l10n_ar_show_generate_delivery_guide)
        self.assertFalse(batch.l10n_ar_show_send_delivery_guide)

    def test_hide_buttons_when_batch_not_done(self):
        """Buttons are hidden when the batch pickings are not yet done."""
        batch, _ = self._create_batch_with_pickings(validate=False)

        self.assertFalse(batch.l10n_ar_show_generate_delivery_guide)
        self.assertFalse(batch.l10n_ar_show_send_delivery_guide)

    def test_show_send_button_after_generation(self):
        """After generating guides, send button appears and generate hides."""
        batch, pickings = self._create_batch_with_pickings()
        pickings.l10n_ar_action_create_delivery_guide()

        self.assertFalse(batch.l10n_ar_show_generate_delivery_guide)
        self.assertTrue(batch.l10n_ar_show_send_delivery_guide)

    # --- Delegation methods --- #

    def test_create_delivery_guide_delegates_to_eligible(self):
        """Only pickings without a guide number get one when called via batch."""
        batch, pickings = self._create_batch_with_pickings()
        # Pre-generate a guide on the first picking
        pickings[0].l10n_ar_action_create_delivery_guide()
        existing_number = pickings[0].l10n_ar_delivery_guide_number

        batch.l10n_ar_action_create_delivery_guide()

        self.assertEqual(pickings[0].l10n_ar_delivery_guide_number, existing_number)
        self.assertTrue(pickings[1].l10n_ar_delivery_guide_number)

    def test_send_delivery_guide_delegates_async(self):
        """Batch send queues eligible pickings for async delivery."""
        batch, pickings = self._create_batch_with_pickings()
        pickings.l10n_ar_action_create_delivery_guide()

        batch.l10n_ar_action_send_delivery_guide()

        for picking in pickings:
            self.assertEqual(picking.l10n_ar_delivery_guide_cron_user_id, self.env.user)
