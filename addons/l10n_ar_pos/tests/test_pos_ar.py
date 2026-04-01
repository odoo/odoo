from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon
from odoo.addons.l10n_ar.tests.common import TestArCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPosAR(AccountTestInvoicingHttpCommon, TestArCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create user.
        cls.pos_user = cls.env['res.users'].create({
            'name': 'A simple PoS man!',
            'login': 'pos_user',
            'password': 'pos_user',
            'email': 'pos_user@test.com',
            'group_ids': [
                (4, cls.env.ref('base.group_user').id),
                (4, cls.env.ref('point_of_sale.group_pos_user').id),
                (4, cls.env.ref('account.group_account_invoice').id),
            ],
        })

        cls.company = cls.company_data['company']
        cls.pos_receivable_bank = cls.copy_account(cls.company.account_default_pos_receivable_account_id, {'name': 'POS Receivable'})
        cls.outstanding_bank = cls.copy_account(cls.outbound_payment_method_line.payment_account_id, {'name': 'Outstanding'})

        cls.bank_pm = cls.env['pos.payment.method'].sudo().create({
            'name': 'Bank',
            'journal_id': cls.company_data['default_journal_bank'].id,
            'receivable_account_id': cls.pos_receivable_bank.id,
            'outstanding_account_id': cls.outstanding_bank.id,
            'company_id': cls.company.id,
        })
        cls.cash_pm = cls.env['pos.payment.method'].sudo().create({
            'name': 'Cash',
            'journal_id': cls.company_data['default_journal_cash'].id,
            'receivable_account_id': cls.pos_receivable_bank.id,
            'outstanding_account_id': cls.outstanding_bank.id,
            'company_id': cls.company.id,
        })

        cls.main_pos_config = cls.env['pos.config'].sudo().create({
            'name': 'Shop',
            'module_pos_restaurant': False,
            'payment_method_ids': [(4, cls.bank_pm.id), (4, cls.cash_pm.id)],
        })

    def test_basic_flow_ar(self):
        self.product_a.available_in_pos = True
        self.product_a.name = "A test product"
        self.main_pos_config.open_ui()
        self.start_tour(f"/pos/ui/{self.main_pos_config.id}", 'PosARBaseFlow', login="pos_user")
