from odoo.tests.common import TransactionCase, tagged
from ..models.main_models import VoucherNumberTastics



@tagged('accountcore')
class Test_account_subsidiary_book(TransactionCase):
    def test_VoucherNumberTastics(self):
        container_str = '{"1": 3}'
        voucher_number = VoucherNumberTastics.get_number(container_str, 1)
        self.assertEqual(voucher_number, 3, '获取对应编号策略的凭证编号有误')

