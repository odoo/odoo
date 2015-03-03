# -*- coding: utf-8 -*-
from openerp.tests import common


class TestContractCommon(common.TransactionCase):

    def setUp(self):
        super(TestContractCommon, self).setUp()
        Contract = self.env['account.analytic.account']
        SaleOrder = self.env['sale.order']
        Product = self.env['product.product']
        ProductTmpl = self.env['product.template']

        # Test products
        self.product_tmpl = ProductTmpl.create({
            'name': 'TestProduct',
            'type': 'service',
            'recurring_invoice': True,
            })
        self.product = Product.create({
            'product_tmpl_id': self.product_tmpl.id,
            'price': 50.0
            })

        # Test user
        TestUsersEnv = self.env['res.users'].with_context({'no_reset_password': True})
        group_portal_id = self.ref('base.group_portal')
        self.user_portal = TestUsersEnv.create({
            'name': 'Beatrice Portal',
            'login': 'Beatrice',
            'alias_name': 'beatrice',
            'email': 'beatrice.employee@example.com',
            'groups_id': [(6, 0, [group_portal_id])]
        })

        # Test Contract
        self.contract_tmpl = Contract.create({
            'name': 'TestContractTemplate',
            'type': 'template',
            'contract_type': 'subscription',
            'recurring_invoice_line_ids': [(0, 0, {'product_id': self.product.id, 'name': 'TestRecurringLine', 'price_unit': self.product.price, 'uom_id': self.product_tmpl.uom_id.id})]
        })
        self.contract = Contract.create({
            'name': 'TestContract',
            'type': 'contract',
            'state': 'open',
            'partner_id': self.user_portal.partner_id.id,
        })
        self.sale_order = SaleOrder.create({
            'name': 'TestSO',
            'project_id': self.contract.id,
            'partner_id': self.user_portal.partner_id.id,
            'order_line': [(0, 0, {'product_id': self.product.id, 'name': 'TestLine'})]
        })
