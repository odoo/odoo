from odoo.tests.common import tagged

from . import common


@tagged("-at_install", "post_install", "post_install_l10n", "mock")
class TestMock(common.TestUyEdiStock):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_uy.write({
            "l10n_uy_edi_ucfe_env": "testing",
            "l10n_uy_edi_ucfe_password": "password_xxx",
            "l10n_uy_edi_ucfe_commerce_code": "commerce_xxx",
            "l10n_uy_edi_ucfe_terminal_code": "terminal_xxx",
        })

    def test_10_delivery_guide_received_pdf_check_status(self):
        """Test successful delivery guide creation"""
        picking = self._create_stock_picking()

        self._mock_create_delivery_guide(picking, "mock_delivery_guide_received", get_pdf=True)
        self.assertEqual(picking.l10n_uy_edi_cfe_state, "received")
        self.assertTrue(picking.l10n_uy_edi_pdf_report_file, "PDF attachment was not created.")

        self._mock_update_dgi_state(picking, "mock_delivery_guide_received")
        self.assertEqual(picking.l10n_uy_edi_cfe_state, "accepted")

    def test_20_delivery_guide_rejected(self):
        """ process an rejected delivery_guide and generate the legal pdf """
        picking = self._create_stock_picking()

        self._mock_create_delivery_guide(picking, "mock_delivery_guide_received", get_pdf=True)
        self.assertEqual(picking.l10n_uy_edi_cfe_state, "received")
        self.assertTrue(picking.l10n_uy_edi_pdf_report_file, "PDF attachment was not created.")

        self._mock_update_dgi_state(picking, "mock_delivery_guide_rejected")
        self.assertEqual(picking.l10n_uy_edi_cfe_state, "rejected")

    def test_30_delivery_guide_error(self):
        """ Capture error returned by DGI because data sent in the XML is not valid """
        partner_local_with_error = self.env["res.partner"].create({
            "name": "IEB Internacional",
            "l10n_latam_identification_type_id": self.env.ref("l10n_uy.it_dni").id,
            "vat": "218435730016",
            "street": "Bach 0",
            "city": "Aeroparque",
            "state_id": self.env.ref("base.state_uy_02").id,
            "country_id": self.env.ref("base.uy").id,
            "email": "rut@example.com",
        })
        picking = self._create_stock_picking(partner_id=partner_local_with_error.id)
        picking.button_validate()

        error_code = "CODE 31"
        error_msg = "se espera país AR, BR, CL ó PY, pero se recibió UY."
        self._mock_create_delivery_guide(picking, "mock_delivery_guide_error")

        self.assertFalse(picking.l10n_uy_edi_pdf_report_file, "Since we have an error the pdf file must not exist.")
        self.assertEqual(picking.l10n_uy_edi_cfe_state, "error")
        self.assertIn(error_code, picking.l10n_uy_edi_error)
        self.assertIn(error_msg, picking.l10n_uy_edi_error)
