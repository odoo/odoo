from odoo.tests.common import tagged

from . import common


@tagged("-at_install", "post_install", "post_install_l10n", "manual")
class TestStockPickingManual(common.TestUyEdiStock):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Set company to demo mode for manual tests
        cls.company_uy.l10n_uy_edi_ucfe_env = "demo"

    def test_10_create_delivery_guide_basic(self):
        """Test basic delivery guide creation and XML generation"""
        picking = self._create_stock_picking()

        # Verify initial state
        self.assertEqual(picking.l10n_latam_document_type_id.code, "181", "Should be e-Remito document type")
        self.assertEqual(picking.l10n_uy_edi_operation_type, "1", "Should be Sale operation")
        self.assertTrue(picking.l10n_uy_is_cfe, "Should be identified as CFE")

        # Validate and create delivery guide
        self._validate_and_create_delivery_guide(picking)

        # Check results
        self.assertEqual(picking.state, "done", "Picking should be done")
        self.assertTrue(picking.l10n_uy_edi_document_id, "EDI document should be created")
        self.assertEqual(picking.l10n_uy_edi_cfe_state, "accepted", "CFE should be accepted in demo mode")

        # Check XML content
        self._check_cfe(picking, "10_delivery_guide_basic")

    def test_20_delivery_guide_internal_transfer(self):
        """Test delivery guide for internal transfer operation"""
        # Create internal location
        location_internal = self.env['stock.location'].create({
            'name': 'Internal Location Test',
            'usage': 'internal',
            'location_id': self.warehouse.lot_stock_id.id,
        })

        picking = self._create_stock_picking(
            location_dest_id=location_internal.id,
            l10n_uy_edi_operation_type='2',  # Internal Transfer
        )

        # Validate and create delivery guide
        self._validate_and_create_delivery_guide(picking)

        # Check XML content for internal transfer
        self._check_cfe(picking, "20_delivery_guide_internal_transfer")

    def test_30_delivery_guide_reversal_with_reference(self):
        """Test delivery guide that reverses (annuls) another document by referencing it"""
        # Create first delivery guide
        original_picking = self._create_stock_picking()
        self._validate_and_create_delivery_guide(original_picking)

        # Create second delivery guide that references the first
        reference_picking = self._create_stock_picking(
            l10n_uy_edi_reference=original_picking.l10n_uy_edi_document_id.id,
        )

        # Validate and create delivery guide
        self._validate_and_create_delivery_guide(reference_picking)

        # Check XML content for reversal with reference
        self._check_cfe(reference_picking, "30_delivery_guide_reversal_with_reference")

        # Check addenda contains reference text
        addenda = reference_picking._l10n_uy_edi_get_addenda()
        self.assertIn(f"Correction of {original_picking.name}", addenda, "Addenda should mention original document")

    def test_40_delivery_guide_with_addenda(self):
        """Test delivery guide with addenda and disclosures"""
        # Create addenda
        addenda = self.env['l10n_uy_edi.addenda'].create({
            'name': 'Test Addenda for Delivery Guide',
            'content': 'Test addenda content for delivery guide',
            'type': 'addenda',
            'is_legend': True,
            'company_id': self.company_uy.id,
        })

        picking = self._create_stock_picking(
            l10n_uy_edi_addenda_ids=[(6, 0, addenda.ids)],
        )

        # Validate and create delivery guide
        self._validate_and_create_delivery_guide(picking)

        # Check XML content for delivery guide with addenda (is the same as basic)
        self._check_cfe(picking, "40_delivery_guide_with_addenda")

        # Check addenda is included
        addenda_content = picking._l10n_uy_edi_get_addenda()
        self.assertIn(addenda.content, addenda_content, "Addenda content should be included")
