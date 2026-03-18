from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from unittest.mock import patch
from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPosQris(TestPointOfSaleHttpCommon):
    """ Testing QRIS payment via PoS """
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    @TestPointOfSaleHttpCommon.setup_chart_template('id')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].qr_code = True
        cls.company_data['company'].partner_id.update({
            'country_id': cls.env.ref('base.id').id,
            'city': 'Jakarta',
        })

        cls.acc_qris_id = cls.env['res.partner.bank'].create({
            'formatted_account_number': '123456789012345678',
            'partner_id': cls.company_data['company'].partner_id.id,
            'l10n_id_qris_api_key': 'apikey',
            'l10n_id_qris_mid': 'mid',
        })

        cls.env['product.combo.item'].search([]).unlink()
        cls.env['product.product'].search([]).write({'available_in_pos': False})

        cls.product_1 = cls.env['product.product'].create({
            'name': 'Test Product',
            'available_in_pos': True,
            'list_price': 1000,
            'taxes_id': False,
        })

        # Create user.
        cls.qris_pos_user = cls.env['res.users'].create({
            'name': 'A simple PoS man!',
            'login': 'qris_pos_user',
            'password': 'qris_pos_user',
            'group_ids': [
                (4, cls.env.ref('base.group_user').id),
                (4, cls.env.ref('point_of_sale.group_pos_user').id),
                (4, cls.env.ref('account.group_account_invoice').id),
            ],
        })

        cls.company = cls.company_data['company']
        cls.pos_receivable_bank = cls.copy_account(cls.company.account_default_pos_receivable_account_id, {'name': 'POS Receivable Bank'})
        cls.outstanding_bank = cls.copy_account(cls.outbound_payment_method_line.payment_account_id, {'name': 'Outstanding Bank'})

        cls.company_data['default_journal_bank'].write({'bank_account_id': cls.acc_qris_id.id})

        cls.bank_pm = cls.env['pos.payment.method'].sudo().create({
            'name': 'Cash',
            'type': 'cash',
            'journal_id': cls.company_data['default_journal_cash'].id,
            'receivable_account_id': cls.pos_receivable_bank.id,
            'company_id': cls.company.id,
        })
        cls.qris_pm = cls.env['pos.payment.method'].sudo().create({
            'name': 'QRIS',
            'type': 'bank',
            'journal_id': cls.company_data['default_journal_bank'].id,
            'receivable_account_id': cls.pos_receivable_bank.id,
            'outstanding_account_id': cls.outstanding_bank.id,
            'company_id': cls.company.id,
            'payment_method_type': 'bank_qr_code',
            'qr_code_method': 'id_qr'
        })

        cls.main_pos_config = cls.env['pos.config'].sudo().create({
            'name': 'Shop',
            'module_pos_restaurant': False,
            # Make sure there is one extra payment method for the tour tests to work.
            # Because if the tour only use the qr payment method, the total amount won't be displayed,
            # causing the tour test to fail.
            'payment_method_ids': [(4, cls.bank_pm.id), (4, cls.qris_pm.id)],
        })

    def test_qris_transaction_allow_pos_order(self):
        """ pos.order model should be created """
        self.env['l10n_id.qris.transaction'].create({
            'model': 'pos.order',
            'model_id': '1234512345'
        })
        self.env['l10n_id.qris.transaction'].create({
            'model': 'account.move',
            'model_id': '1'
        })

        with self.assertRaises(ValidationError):
            self.env['l10n_id.qris.transaction'].create({
                'model': 'new.model',
                'model_id': '1',
            })

    def test_qris_link_with_pos_order(self):
        """ Test whether it's possible to link QRIS transaction with a pos.order record through
        UUID field instead of id """
        self.main_pos_config.with_user(self.qris_pos_user).open_ui()
        pos_order = self.env['pos.order'].with_user(self.qris_pos_user).create({
            'company_id': self.env.company.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'partner_id': self.partner_a.id,
            'access_token': '1234567890',
            'uuid': '1234512345',
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product_1.id,
                'price_unit': 10000,
                'discount': 0.0,
                'qty': 1.0,
                'tax_ids': False,
                'price_subtotal': 10,
                'price_subtotal_incl': 10,
            })],
            'amount_tax': 0,
            'amount_total': 10,
            'amount_paid': 10.0,
            'amount_return': 10.0,
        })
        qris_transaction = self.env['l10n_id.qris.transaction'].create({
            'model': 'pos.order',
            'model_id': '1234512345',
        })

        record = qris_transaction._get_record()
        self.assertEqual(pos_order, record)

    def test_qris_qr_code_value(self):
        """ The QR-code image is drawn by the PoS client, so the server has to return the
        raw QRIS payload the bank app expects, and not the URL of the report rendering it.
        """
        qris_content = "00020101021226610014COM.QRIS.WWW011893600914123456789002150000000000000000303UMI51440014ID.CO.QRIS.WWW0215ID10200211817450303UMI5204541153033605802ID5910Odoo Store6007JAKARTA6304A1B2"

        def _patched_make_qris_request(endpoint, params):
            return {
                "status": "success",
                "data": {
                    "qris_content": qris_content,
                    "qris_request_date": "2024-02-27 11:13:42",
                    "qris_invoiceid": "413255111",
                    "qris_nmid": "ID1020021181745",
                },
            }

        with patch('odoo.addons.l10n_id.models.res_bank._l10n_id_make_qris_request', side_effect=_patched_make_qris_request):
            qr_value = self.qris_pm.get_qr_code_value(1000, 'Order 00042', '', self.company.currency_id.id, False)

        self.assertEqual(qr_value, qris_content)

    def test_tour_qris_payment_fail(self):
        """ Add products, show QR code and confirm. When confirming, the result will be status
        unpaid and so it should trigger a warning dialog informing it"""

        def _patched_make_qris_request(endpoint, params):
            if endpoint == 'show_qris.php':
                self.assertTrue(params['cliTrxNumber'])
                return {
                    "status": "success",
                    "data": {
                        "qris_content": "Test Content",
                        "qris_request_date": "2024-02-27 11:13:42",
                        "qris_invoiceid": "413255111",
                        "qris_nmid": "ID1020021181745"
                    }
                }
            elif endpoint == 'checkpaid_qris.php':
                return {
                    "status": "failed",
                    "data": {
                        "qris_status": "unpaid"
                    }
                }

        self.main_pos_config.with_user(self.qris_pos_user).open_ui()
        with patch('odoo.addons.l10n_id.models.res_bank._l10n_id_make_qris_request', side_effect=_patched_make_qris_request):
            self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PaymentScreenQRISPaymentFail', login="qris_pos_user")

    def test_tour_qris_payment_success(self):
        """ Successful fetching status should proceed next to go to receipt screen"""
        def _patched_make_qris_request(endpoint, params):
            if endpoint == 'show_qris.php':
                return {
                    "status": "success",
                    "data": {
                        "qris_content": "Test Content",
                        "qris_request_date": "2024-02-27 11:13:42",
                        "qris_invoiceid": "413255111",
                        "qris_nmid": "ID1020021181745"
                    }
                }
            elif endpoint == 'checkpaid_qris.php':
                return {
                    "status": "success",
                    "data": {
                        "qris_status": "paid",
                        "qris_payment_customername": "Zainal Arief",
                        "qris_payment_methodby": "Sakuku"
                    },
                    "qris_api_version_code": "2206091709"
                }
        self.main_pos_config.with_user(self.qris_pos_user).open_ui()
        with patch('odoo.addons.l10n_id.models.res_bank._l10n_id_make_qris_request', side_effect=_patched_make_qris_request):
            self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PaymentScreenQRISPaymentSuccess', login="qris_pos_user")

    @freeze_time("2024-02-27 04:15:00")
    def test_only_call_api_call_once(self):
        """ Simulate generating QR, cancel the popup, when we click show QR again, it shouldn't trigger
        to fetch new QR code from QRIS"""
        def _patched_make_qris_request(endpoint, params):
            if endpoint == 'show_qris.php':
                return {
                    "status": "success",
                    "data": {
                        "qris_content": "Test Content",
                        "qris_request_date": "2024-02-27 11:13:42",
                        "qris_invoiceid": "413255111",
                        "qris_nmid": "ID1020021181745"
                    }
                }
            elif endpoint == 'checkpaid_qris.php':
                return {
                    "status": "success",
                    "data": {
                        "qris_status": "paid",
                        "qris_payment_customername": "Zainal Arief",
                        "qris_payment_methodby": "Sakuku"
                    },
                    "qris_api_version_code": "2206091709"
                }
        self.main_pos_config.with_user(self.qris_pos_user).open_ui()
        with patch('odoo.addons.l10n_id.models.res_bank._l10n_id_make_qris_request', side_effect=_patched_make_qris_request) as patched:
            self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PayementScreenQRISFetchQR', login="qris_pos_user")
            self.assertEqual(patched.call_count, 1)

    @freeze_time("2024-02-27 04:15:00")
    def test_qris_change_amount(self):
        """ Test that when user changes the amount of order after generating QRIS QR for the first time,
        it should request for new QR code afterwards. Therefore, there should be 2 API calls instead"""
        def _patched_make_qris_request(endpoint, params):
            if endpoint == 'show_qris.php':
                return {
                    "status": "success",
                    "data": {
                        "qris_content": "Test Content",
                        "qris_request_date": "2024-02-27 11:13:42",
                        "qris_invoiceid": "413255111",
                        "qris_nmid": "ID1020021181745"
                    }
                }
        self.main_pos_config.with_user(self.qris_pos_user).open_ui()
        self.main_pos_config.current_session_id.set_opening_control(0, 'notes')
        with patch('odoo.addons.l10n_id.models.res_bank._l10n_id_make_qris_request', side_effect=_patched_make_qris_request) as patched:
            self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PayementScreenQRISChangeAmount', login="qris_pos_user")
            self.assertEqual(patched.call_count, 3)
