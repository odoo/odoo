# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.tests import tagged
from odoo.addons.l10n_ke_edi_oscu.tests.test_live import TestKeEdi


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestKeEdiMocked(TestKeEdi):

    @classmethod
    @TestKeEdi.setup_country('ke')
    def setUpClass(cls):
        with freeze_time('2024-04-15'):
            super().setUpClass()

    def test_get_items(self):
        with freeze_time('2024-04-15'), self.patch_session([
            ('selectItemList', 'get_from_last_request', 'get_items'),
        ]):
            self._test_get_items()

    def test_get_stock_moves(self):
        with freeze_time('2024-04-15'), self.patch_session([
            ('selectStockMoveList', 'get_from_last_request', 'get_stock_moves'),
        ]):
            self._test_get_stock_moves()

    def test_update_codes(self):
        with freeze_time('2024-04-15'), self.patch_session([
            ('selectCodeList', 'get_from_last_request', 'get_codes'),
        ]):
            self._test_update_codes()

    def test_update_customer(self):
        with freeze_time('2024-04-15'), self.patch_session([
            ('selectCustomer', 'get_customer', 'get_customer'),
        ]):
            self._test_update_customer()

    def test_update_notices(self):
        with freeze_time('2024-04-15'), self.patch_session([
            ('selectNoticeList', 'get_from_last_request', 'get_notices'),
        ]):
            self._test_update_notices()

    def test_update_unspsc_codes(self):
        with freeze_time('2024-04-15'), self.patch_session([
            ('selectItemClsList', 'get_from_last_request', 'get_unspsc_codes'),
        ]):
            self._test_update_unspsc_codes()

    def test_save_customer(self):
        with freeze_time('2024-04-15'), self.patch_session([
            ('saveBhfCustomer', 'save_customer', 'success'),
        ]):
            self._test_save_customer()

    def test_save_insurance(self):
        with freeze_time('2024-04-15'), self.patch_session([
            ('saveBhfInsurance', 'save_insurance', 'success'),
        ]):
            self._test_save_insurance()

    def test_save_item(self):
        with freeze_time('2024-04-15'), self.patch_session([
            ('saveItem', 'save_item_0', 'success'),
        ]):
            self._test_save_item()

    def test_save_user(self):
        with freeze_time('2024-04-15'), self.patch_session([
            ('saveBhfUser', 'save_user', 'success'),
        ]):
            self._test_save_user()

    def test_create_branches(self):
        with freeze_time('2024-04-15'), self.patch_session([
            ('selectBhfList', 'get_branches', 'get_branches'),
        ]):
            self._test_create_branches()

    def test_send_invoice_and_credit_note(self):
        with freeze_time('2024-04-15'), self.patch_session([
            ('saveItem', 'save_item_0', 'success'),
            ('saveTrnsSalesOsdc', 'save_sale_1', 'save_sale_success'),
            ('selectInvoiceDetails', 'get_invoice_details_1', 'get_invoice_details_success'),
            ('saveTrnsSalesOsdc', 'save_refund_1', 'save_sale_success'),
        ]):
            self._test_send_invoice_and_credit_note()

    def test_send_invoice_complex(self):
        with freeze_time('2024-04-15'), self.patch_session([
            ('saveItem', 'save_item_0', 'success'),
            ('saveTrnsSalesOsdc', 'save_sale_complex', 'save_sale_success'),
        ]):
            self._test_send_invoice_complex()

    def test_confirm_vendor_bill(self):
        with freeze_time('2024-04-15'), self.patch_session([
            ('selectTrnsPurchaseSalesList', 'get_purchases', 'get_purchases_1'),
            ('saveItem', 'save_item_0', 'success'),
            ('insertTrnsPurchase', 'save_purchase_1', 'success'),
        ]):
            vendor_bill = self._test_get_vendor_bill()
            self._test_confirm_vendor_bill(vendor_bill)
