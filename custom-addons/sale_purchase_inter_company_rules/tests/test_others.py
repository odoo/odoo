from .common import TestInterCompanyRulesCommonSOPO
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestInterCompanyOthers(TestInterCompanyRulesCommonSOPO):

    def test_00_auto_purchase_on_normal_sales_order(self):
        partner1 = self.env['res.partner'].create({'name': 'customer', 'email': 'from.customer@example.com'})
        my_service = self.env['product.product'].create({
            'name': 'my service',
            'type': 'service',
            'service_to_purchase': True,
            'seller_ids': [(0, 0, {
                'partner_id': self.company_a.partner_id.id,
                'min_qty': 1,
                'price': 10,
                'product_code': 'C01',
                'product_name': 'Name01',
                'sequence': 1,
            })]
        })
        so = self.env['sale.order'].create({
            'partner_id': partner1.id,
            'order_line': [
                (0, 0, {
                    'name': my_service.name,
                    'product_id': my_service.id,
                    'product_uom_qty': 1,
                })
            ],
        })
        # confirming the action from the test will use Odoobot which results in the same flow as
        # confirming the SO from an email link
        so.action_confirm()

        po = self.env['purchase.order'].search([('partner_id', '=', self.company_a.partner_id.id)], order='id desc',
                                               limit=1)
        self.assertEqual(po.order_line.name, "[C01] Name01")
