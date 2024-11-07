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
        cls.invoice = cls.init_invoice(
            "out_invoice",
            post=True,
            products=cls.product_a,
            partner=cls.partner_a
        )
        attachment = cls.env['ir.attachment'].create({
            'name': 'einvoice.json',
            'res_model': 'account.move',
            'res_id': cls.invoice.id,
            'raw': b'{"Irn": "1234567890"}',
        })
        cls.invoice.write({
            "l10n_in_edi_status": "sent",
            "l10n_in_edi_attachment_id": attachment.id,
        })

    def test_ewaybill_irn(self):
        ewaybill = self.env['l10n.in.ewaybill'].create({
            'account_move_id': self.invoice.id,
            'distance': 20,
            'mode': "1",
            'vehicle_no': "GJ11AA1234",
            'vehicle_type': "R",
        })
        self.assertTrue(ewaybill.is_process_through_irn)
        self.assertDictEqual(
            ewaybill._ewaybill_generate_irn_json(),
            {
                'Irn': "1234567890",
                'Distance': '20',
                'TransMode': '1',
                'VehNo': 'GJ11AA1234',
                'VehType': 'R'
            }
        )
