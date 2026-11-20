from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericIN(TestGenericLocalization, CommonPosTest):

    _pos_partner_pos_form_fields = ['l10n_in_gst_treatment']
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    @AccountTestInvoicingCommon.setup_country('in')
    def setUpClass(cls):
        super().setUpClass()
        cls.state_in_gj = cls.env.ref('base.state_in_gj')
        cash_pm = cls.main_pos_config.payment_method_ids.filtered_domain([
            ('type', '=', 'cash'),
        ])
        if not cls.main_pos_config._get_cash_payment_method():
            cls.main_pos_config.write({
                'payment_method_ids': [(4, cash_pm[0].id)],
            })
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
        order, html = super().test_generic_localization()
        self.assertTrue("HSN Code" in html)
        # The customer is a company: the order is invoiced on request (B2B).
        self.assertFalse(order.l10n_in_b2c_invoice_number)
        self.assertIn(order.account_move.name, html)

    def test_refund_order_receipt(self):
        _, refund = self.create_backend_pos_order({
            'pos_config': self.main_pos_config,
            'order_data': {
                'partner_id': self.partner_b.id,  # Without GSTIN: B2C order
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
        self.assertTrue(refund.l10n_in_b2c_invoice_number.startswith('R'))
        self.assertIn(refund.l10n_in_b2c_invoice_number, refund.order_receipt_generate_html())
