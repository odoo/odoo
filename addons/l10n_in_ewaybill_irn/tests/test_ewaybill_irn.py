from freezegun import freeze_time
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestEwaybillJson(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.write({
            "l10n_in_edi_feature": True
        })
        cls.invoice_a = cls.init_invoice(
            "out_invoice",
            post=True,
            products=cls.product_a,
            partner=cls.partner_a
        )
        cls.invoice_b = cls.init_invoice(
            "out_invoice",
            post=True,
            products=cls.product_a,
            partner=cls.partner_foreign
        )
        cls.partner_foreign_address = cls.env['res.partner'].create({
            'name': "Foreign Partner Port Address",
            'commercial_partner_id': cls.partner_foreign.id,
            'country_id': cls.country_in.id,
            'state_id': cls.state_in_gj.id,
            'street': "Post Box No. 1 Mundra",
            'city': "Kutch",
            'zip': "370421",
        })
        attachment_a = cls.env['ir.attachment'].create({
            'name': 'einvoice_a.json',
            'res_model': 'account.move',
            'res_id': cls.invoice_a.id,
            'raw': b'{"Irn": "1234567890"}',
        })
        attachment_b = cls.env['ir.attachment'].create({
            'name': 'einvoice_b.json',
            'res_model': 'account.move',
            'res_id': cls.invoice_b.id,
            'raw': b'{"Irn": "1234567890"}',
        })
        cls.invoice_a.write({
            "l10n_in_edi_status": "sent",
            "l10n_in_edi_attachment_id": attachment_a.id,
        })
        cls.invoice_b.write({
            "l10n_in_edi_status": "sent",
            "l10n_in_edi_attachment_id": attachment_b.id,
        })
        cls.invoice_b.l10n_in_gst_treatment = 'overseas'

    def test_ewaybill_irn(self):
        ewaybill_a = self.env['l10n.in.ewaybill'].create({
            'account_move_id': self.invoice_a.id,
            'distance': 20,
            'mode': "1",
            'vehicle_no': "GJ11AA1234",
            'vehicle_type': "R",
        })
        ewaybill_b = self.env['l10n.in.ewaybill'].create({
            'account_move_id': self.invoice_b.id,
            'distance': 20,
            'mode': "1",
            'vehicle_no': "GJ11AA1234",
            'vehicle_type': "R",
        })
        ewaybill_b.write({
            'partner_ship_to_id': self.partner_foreign_address.id,
        })
        self.assertTrue(ewaybill_a.is_process_through_irn)
        self.assertTrue(ewaybill_b.is_process_through_irn)
        self.assertDictEqual(
            ewaybill_a._ewaybill_generate_irn_json(),
            {
                'Irn': "1234567890",
                'Distance': '20',
                'TransMode': '1',
                'VehNo': 'GJ11AA1234',
                'VehType': 'R',
                'DispDtls': {
                    'Addr1': 'Khodiyar Chowk',
                    'Loc': 'Amreli',
                    'Pin': 365220,
                    'Stcd': '24',
                    'Addr2': 'Sala Number 3',
                    'Nm': 'Default Company'
                }
            }
        )
        self.assertDictEqual(
            ewaybill_b._ewaybill_generate_irn_json(),
            {
                'Irn': "1234567890",
                'Distance': '20',
                'TransMode': '1',
                'VehNo': 'GJ11AA1234',
                'VehType': 'R',
                'DispDtls': {
                    'Addr1': 'Khodiyar Chowk',
                    'Loc': 'Amreli',
                    'Pin': 365220,
                    'Stcd': '24',
                    'Addr2': 'Sala Number 3',
                    'Nm': 'Default Company'
                },
                'ExpShipDtls': {
                    'Addr1': 'Post Box No. 1 Mundra',
                    'Loc': 'Kutch',
                    'Pin': 370421,
                    'Stcd': '24'
                }
            }
        )

        # Unregistered Transporter (No GSTIN)
        self.partner_b.write({
            'vat': False,
            'name': 'Atlas'
        })
        ewaybill_a.transporter_id = self.partner_b
        self.assertDictEqual(
            ewaybill_a._ewaybill_generate_irn_json(),
            {
                'Irn': '1234567890',
                'Distance': '20',
                'TransMode': '1',
                'TransName': 'Atlas',
                'VehNo': 'GJ11AA1234',
                'VehType': 'R',
                'DispDtls': {
                    'Addr1': 'Khodiyar Chowk',
                    'Loc': 'Amreli',
                    'Pin': 365220,
                    'Stcd': '24',
                    'Addr2': 'Sala Number 3',
                    'Nm': 'Default Company'
                }
            }
        )
