# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import users

from odoo.addons.sale.tests.common import SaleCommon
from odoo.addons.sales_team.tests.common import TestSalesCommon


class TestSaleOrderCancel(SaleCommon, TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env.ref('sale.mail_template_sale_cancellation')
        cls.template.write({
            'subject': 'I can see {{ len(object.partner_id.sale_order_ids) }} order(s)',
            'body_html': 'I can see <t t-out="len(object.partner_id.sale_order_ids)"/> order(s)',
        })

        cls.partner = cls.env['res.partner'].create({'name': 'foo'})

        cls.manager_order, cls.salesman_order = cls.env['sale.order'].create([
            {'partner_id': cls.partner.id, 'user_id': cls.user_sales_manager.id},
            {'partner_id': cls.partner.id, 'user_id': cls.user_sales_salesman.id}
        ])
        # Invalidate the cache, e.g. to clear the computation of partner.sale_order_ids
        cls.env.invalidate_all()

    @users('user_sales_salesman')
    def test_salesman_record_rules(self):
        cancel = self.env['sale.order.cancel'].create({
            'template_id': self.template.id,
            'order_id': self.salesman_order.id,
        })

        self.assertEqual(cancel.subject, 'I can see 1 order(s)')
        self.assertEqual(cancel.body, '<p>I can see 1 order(s)</p>')

    @users('user_sales_manager')
    def test_manager_record_rules(self):
        cancel = self.env['sale.order.cancel'].create({
            'template_id': self.template.id,
            'order_id': self.manager_order.id,
        })

        self.assertEqual(cancel.subject, 'I can see 2 order(s)')
        self.assertEqual(cancel.body, '<p>I can see 2 order(s)</p>')
