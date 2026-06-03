from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
<<<<<<< 5da7065b46b8654aa7816c328f17a9b21e5cca82
class TestGenericIN(TestGenericLocalization, CommonPosTest):
||||||| 153106e376748aafa90767f544bbf0c58aab7005
class TestGenericIN(TestGenericLocalization):
=======
class TestGenericIN(TestGenericLocalization):
    pos_partner_pos_form_fields = ['l10n_in_gst_treatment']
>>>>>>> 84a4fd86794a7bbac6bb0b057706a86cdc90856d

    @classmethod
    @AccountTestInvoicingCommon.setup_country('in')
    def setUpClass(cls):
        super().setUpClass()
        cls.state_in_gj = cls.env.ref('base.state_in_gj')
        cls.main_pos_config.company_id.write({
            'name': "Default Company",
            'state_id': cls.state_in_gj.id,
            'vat': "24AAGCC7144L6ZE",
            'street': "Khodiyar Chowk",
            'street2': "Sala Number 3",
            'city': "Amreli",
            'zip': "365220",
        })
        cls.whiteboard_pen.write({
            'l10n_in_hsn_code': '1111',
        })

        cls.wall_shelf.write({
            'l10n_in_hsn_code': '2222',
        })

    def test_generic_localization(self):
        _, html = super().test_generic_localization()
        self.assertTrue("HSN Code" in html)
        self.assertTrue("Tax Invoice" in html)

    def _get_refund_receipt_html(self, to_invoice=False):
        _, refund = self.create_backend_pos_order({
            'pos_config': self.main_pos_config,
            'order_data': {
                'partner_id': self.partner_a.id,
                'to_invoice': to_invoice,
            },
            'line_data': [
                {'product_id': self.product_a.id},
            ],
            'payment_data': [
                {
                    'payment_method_id': self.main_pos_config.payment_method_ids[0].id,
                }
            ],
            'refund_data': [
                {
                    'payment_method_id': self.main_pos_config.payment_method_ids[0].id,
                }
            ],
        })
        return refund.order_receipt_generate_html()

    def test_refund_order_receipt(self):
        self.assertIn("R-INVOICE", self._get_refund_receipt_html())

    def test_refund_invoice_order_receipt(self):
        self.assertIn("Tax R-Invoice", self._get_refund_receipt_html(to_invoice=True))
