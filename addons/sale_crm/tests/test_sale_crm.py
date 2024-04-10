from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.fields import Command


class TestSaleCrm(TestCrmCommon):

    def test_sale_crm_revenue(self):
        """ Test the updation of the expected_revenue when the is confirmed.
        If the expected_revenue of the lead is smaller than the total of quote which we are confirming, update it with that.
        e.g. if the lead has a expected revenue of 40 $
        Quotes - q1 = 45$
        ===> The expected_revenue would be updated, from 40 to 45$.
        """
        product1, product2 = self.env['product.template'].create([{
            'name': 'Test product1',
            'list_price': 100.0,
        }, {
            'name': 'Test product2',
            'list_price': 200.0,
        }])

        my_pricelist = self.env['product.pricelist'].create({
            'name': 'Rupee',
            'currency_id': self.ref('base.INR')
        })
        pricelist_expected_by_lead = self.env['product.pricelist'].create({
            'name': 'Rupee',
            'currency_id': self.ref('base.USD')
        })

        so_values = {
            'partner_id': self.env.user.partner_id.id,
            'opportunity_id': self.lead_1.id,
        }
        so1, so2 = self.env['sale.order'].create([{
            **so_values,
            'pricelist_id': my_pricelist.id,
            'order_line': [
                Command.create({
                    'product_id': product1.product_variant_id.id,
                }),
            ],
        }, {
            **so_values,
            'pricelist_id': pricelist_expected_by_lead.id,
            'order_line': [
                Command.create({
                    'product_id': product2.product_variant_id.id,
                }),
            ],
        }])

        self.assertEqual(self.lead_1.expected_revenue, 0)

        # Revenue should not be updated when the currency of sale order is different from lead.
        so1.action_confirm()
        self.assertEqual(self.lead_1.expected_revenue, 0)
        # Revenue should be updated when the currency is same.
        so2.action_confirm()
        self.assertEqual(self.lead_1.expected_revenue, 200)
