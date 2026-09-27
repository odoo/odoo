from odoo.addons.account_edi.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericPE(TestGenericLocalization):

    _pos_partner_pos_form_fields = ['vat', 'additional_identifiers', 'l10n_pe_district']
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pe')
    def setUpClass(cls):
        super().setUpClass()


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestPePosReceipt(TestPointOfSaleHttpCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('pe')
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Luigys Toro',
            'country_id': cls.env.ref('base.pe').id,
            'additional_identifiers': {'PE_DNI': '70025425'},
        })

    def test_receipt_partner_vat_label(self):
        self.main_pos_config.open_ui()
        order = self.env['pos.order'].create({
            'session_id': self.main_pos_config.current_session_id.id,
            'partner_id': self.partner.id,
            'amount_total': 0,
            'amount_paid': 0,
            'amount_tax': 0,
            'amount_return': 0,
        })

        data = order.order_receipt_generate_data()
        self.assertEqual(data['extra_data']['partner_vat_label'], 'DNI')
        self.assertEqual(data['partner']['vat'], '70025425')
