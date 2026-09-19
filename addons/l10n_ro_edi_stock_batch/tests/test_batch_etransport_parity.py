from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_ro_edi_stock.tests.common import TestL10nRoEdiStockCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestBatchETransportParity(TestL10nRoEdiStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Consignee"})
        cls.product = cls.env["product.product"].create(
            {"name": "Freighted", "is_storable": True, "weight": 1.0}
        )
        cls.internal_type = cls.env["stock.picking.type"].create(
            {
                "name": "Parity Internal",
                "code": "internal",
                "sequence_code": "PARINT",
                "company_id": cls.env.company.id,
                "warehouse_id": cls.warehouse.id,
                "default_location_src_id": cls.warehouse.lot_stock_id.id,
                "default_location_dest_id": cls.warehouse.lot_stock_id.id,
            }
        )

    def _make_picking(self, picking_type=None):
        return self.create_stock_picking(
            self.partner,
            picking_type=picking_type,
            product_data=[
                {"product_id": self.product, "product_uom_qty": 1, "quantity": 1}
            ],
        )

    def _make_batch(self, pickings, picking_type=None):
        return self.env["stock.picking.batch"].create(
            {
                "picking_type_id": (picking_type or self.warehouse.out_type_id).id,
                "picking_ids": [Command.set(pickings.ids)],
            }
        )

    def _document(self, host_field, host, state):
        return self.env["l10n_ro_edi.document"].create(
            {host_field: host.id, "state": state, "message": state}
        )

    def _validated_then_failed(self, host_field, host):
        self._document(host_field, host, "stock_validated")
        self._document(host_field, host, "stock_sending_failed")
        host.invalidate_recordset()

    def test_an_internal_transfer_files_no_declaration_and_offers_no_amend(self):
        picking = self._make_picking(picking_type=self.internal_type)
        self._validated_then_failed("picking_id", picking)
        self.assertEqual(picking.picking_type_code, "internal")
        self.assertFalse(picking.l10n_ro_edi_stock_enable)
        self.assertEqual(picking.l10n_ro_edi_stock_state, "stock_sending_failed")
        self.assertTrue(picking._l10n_ro_edi_stock_get_last_document("stock_validated"))
        self.assertFalse(
            picking.l10n_ro_edi_stock_enable_amend,
            "Both amend operands hold, so only the guard on enable keeps this "
            "False. That guard is what the batch copy loses to operator "
            "precedence.",
        )

    def test_a_batch_offers_amend_on_the_same_terms_as_a_transfer(self):
        batch = self._make_batch(self._make_picking())
        self._validated_then_failed("batch_id", batch)
        self.assertTrue(batch.l10n_ro_edi_stock_enable)
        self.assertTrue(batch.l10n_ro_edi_stock_enable_amend)

    def test_the_batch_amend_defect_is_dormant_because_state_is_gated_too(self):
        batch = self._make_batch(self._make_picking())
        self._validated_then_failed("batch_id", batch)
        batch.company_id.account_config_id.account_fiscal_country_id = self.env.ref(
            "base.be"
        )
        batch.invalidate_recordset()
        self.assertFalse(batch.l10n_ro_edi_stock_enable)
        self.assertFalse(
            batch.l10n_ro_edi_stock_state,
            "The state compute carries the same Romania test as enable, so "
            "enable False forces state False.",
        )
        self.assertFalse(
            batch.l10n_ro_edi_stock_enable_amend,
            "Written as `enable and A or (B and C)` this binds as "
            "`(enable and A) or (B and C)` and loses the guard on enable. It "
            "is unreachable only while state is gated by the same condition. "
            "Give enable a second guard, such as the transfer copy's test on "
            "internal operations, and the defect wakes up.",
        )

    def test_a_batch_of_internal_transfers_still_enables_etransport(self):
        internal = self.internal_type
        picking = self._make_picking(picking_type=internal)
        batch = self._make_batch(picking, picking_type=internal)
        self.assertFalse(picking.l10n_ro_edi_stock_enable)
        self.assertTrue(
            batch.l10n_ro_edi_stock_enable,
            "Divergence between the two copies: the transfer excludes "
            "internal operations and the batch does not.",
        )

    def test_a_batch_may_send_before_it_is_done_and_a_transfer_may_not(self):
        picking = self._make_picking()
        picking.action_confirm()
        batch = self._make_batch(picking)
        batch.action_confirm()
        batch.invalidate_recordset()
        picking.invalidate_recordset()
        self.assertNotEqual(picking.state, "done")
        self.assertFalse(picking.l10n_ro_edi_stock_enable_send)
        self.assertTrue(
            batch.l10n_ro_edi_stock_enable_send,
            "Second divergence: the transfer requires done, the batch only "
            "requires not draft.",
        )

    def test_a_transfer_in_a_batch_files_through_the_batch_and_not_itself(self):
        picking = self._make_picking()
        self.assertTrue(picking.l10n_ro_edi_stock_enable)
        self._make_batch(picking)
        picking.invalidate_recordset()
        self.assertFalse(
            picking.l10n_ro_edi_stock_enable,
            "This is the whole reason the bridge overrides the compute.",
        )

    def test_the_bridge_does_not_widen_which_companies_may_file(self):
        picking = self._make_picking()
        company = picking.company_id
        company.account_config_id.account_fiscal_country_id = self.env.ref("base.be")
        picking.invalidate_recordset()
        self.assertEqual(company.country_id.code, "RO")
        self.assertFalse(
            picking.l10n_ro_edi_stock_enable,
            "The override read company_id.country_id where the module it "
            "overrides reads account_fiscal_country_id, so installing this "
            "bridge decided eTransport by the postal address instead of the "
            "fiscal country.",
        )
