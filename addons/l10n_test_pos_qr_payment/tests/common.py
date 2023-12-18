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

        cls.main_pos_config = cls.env['pos.config'].create({
            'name': 'Shop',
            'module_pos_restaurant': False,
        })
