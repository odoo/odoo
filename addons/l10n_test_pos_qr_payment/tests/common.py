# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


class TestPosQrCommon(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].qr_code = True

        cls.product_1 = cls.env['product.product'].create({
            'name': 'Hand Bag',
            'available_in_pos': True,
            'list_price': 4.8,
            'taxes_id': False,
        })

        # Create user.
        cls.pos_user = cls.env['res.users'].create({
            'name': 'A simple PoS man!',
            'login': 'pos_user',
            'password': 'pos_user',
            'groups_id': [
                (4, cls.env.ref('base.group_user').id),
                (4, cls.env.ref('point_of_sale.group_pos_user').id),
                (4, cls.env.ref('account.group_account_invoice').id),
            ],
        })

        cls.company = cls.company_data['company']
        cls.pos_receivable_bank = cls.copy_account(cls.company.account_default_pos_receivable_account_id, {'name': 'POS Receivable Bank'})
        cls.outstanding_bank = cls.copy_account(cls.inbound_payment_method_line.payment_account_id, {'name': 'Outstanding Bank'})
        cls.bank_pm = cls.env['pos.payment.method'].create({
            'name': 'Bank',
            'journal_id': cls.company_data['default_journal_bank'].id,
            'receivable_account_id': cls.pos_receivable_bank.id,
            'outstanding_account_id': cls.outstanding_bank.id,
            'company_id': cls.company.id,
        })

        cls.main_pos_config = cls.env['pos.config'].create({
            'name': 'Shop',
            'module_pos_restaurant': False,
            'journal_id': cls.company_data['default_journal_sale'].id,
            # Make sure there is one extra payment method for the tour tests to work.
            # Because if the tour only use the qr payment method, the total amount won't be displayed,
            # causing the tour test to fail.
            'payment_method_ids': [(4, cls.bank_pm.id)]
        })
