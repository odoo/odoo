from odoo import _
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestWarning(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('in')
    def setUpClass(cls):
        super().setUpClass()
        country_in_id = cls.env.ref("base.in").id
        cls.company_data["company"].write({
            "vat": "24AAGCC7144L6ZE",
            "state_id": cls.env.ref("base.state_in_gj").id,
            "street": "street1",
            "city": "city1",
            "zip": "123456",
            "country_id": country_in_id,
        })
        cls.env.company = cls.company_data["company"]
        cls.partner_c = cls.env['res.partner'].create({
            'name': "Overseas partner",
            'l10n_in_gst_treatment': 'overseas',
            'state_id': cls.env.ref("base.state_us_1").id,
            'country_id': cls.env.ref("base.us").id,
            'zip': "123456",
        })
        cls.igst_18 = cls.env['account.chart.template'].ref('igst_sale_18')
        cls.igst_0 = cls.env['account.chart.template'].ref('igst_sale_0')
        cls.gst_18 = cls.env['account.chart.template'].ref('sgst_sale_18')

    def test_l10n_in_warnings_for_oversea_invoice(self):
        # oversea invoice with igst taxes
        out_invoice_igst = self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_c,
            amounts=[40, 160, 25],
            taxes=[self.igst_18, self.igst_0]
        )
        self.assertRecordValues(
            out_invoice_igst,
            [{
                'state': 'draft',
                'l10n_in_gst_treatment': self.partner_c.l10n_in_gst_treatment,
                'l10n_in_state_id': self.env.ref("l10n_in.state_in_oc").id,
                'l10n_in_warnings': False
            }]
        )

        # oversea invoice with gst taxes
        out_invoice_gst = self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_c,
            amounts=[160, 25],
            taxes=[self.gst_18]
        )
        expected_warnings = {}
        expected_warnings['invalid_gst_type_on_overseas_invoice'] = {
            'message': _("IGST should be used when the place of supply is a foreign country."),
            'level': 'warning',
        }
        self.assertRecordValues(
            out_invoice_gst,
            [{
                'state': 'draft',
                'l10n_in_gst_treatment': self.partner_c.l10n_in_gst_treatment,
                'l10n_in_state_id': self.env.ref("l10n_in.state_in_oc").id,
                'l10n_in_warnings': expected_warnings
            }]
        )
