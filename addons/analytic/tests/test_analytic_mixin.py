from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestAnalyticMixin(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Plan',
        })

        cls.sales_aa = cls.env['account.analytic.account'].create({'name': 'Sales', 'plan_id': cls.analytic_plan.id})
        cls.administrative_aa = cls.env['account.analytic.account'].create({'name': 'Administrative', 'plan_id': cls.analytic_plan.id})
        cls.rd_aa = cls.env['account.analytic.account'].create({'name': 'Research & Development', 'plan_id': cls.analytic_plan.id})
        cls.commercial_aa = cls.env['account.analytic.account'].create({'name': 'Commercial', 'plan_id': cls.analytic_plan.id})
        cls.marketing_aa = cls.env['account.analytic.account'].create({'name': 'Marketing', 'plan_id': cls.analytic_plan.id})
        cls.com_marketing_aa = cls.env['account.analytic.account'].create({'name': 'Commercial & Marketing', 'plan_id': cls.analytic_plan.id})

        cls.product_a = cls.env['product.product'].create({
            'name': 'product_a',
            'lst_price': 1000.0,
        })

    def test_filtered_domain(self):
        """
            This test covers the filtered_domain override on analytic.mixin.
            It is supposed to handle the use of analytic_distribution with the following operators
            with a string representing the analytic account name :
                - `=`
                - `!=`
                - `ilike`,
                - `not ilike`,
            and the "in" operator used to directly indicate a tuple/list of analytic account ids.
            This test verifies that the public method handles all these operators.
        """
        self.move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2023-02-01',
            'invoice_date': '2023-02-01',
            'invoice_line_ids': []
        })

        self.aml_sales_admin_ad = self.env['account.move.line'].create({
            'product_id': self.product_a.id,
            'price_unit': 1000.0,
            'analytic_distribution': {
                self.sales_aa.id: 50,
                self.administrative_aa.id: 50
            },
            'move_id': self.move.id
        })

        self.aml_rd_ad = self.env['account.move.line'].create({
            'product_id': self.product_a.id,
            'price_unit': 1000.0,
            'analytic_distribution': {
                self.rd_aa.id: 100,
            },
            'move_id': self.move.id
        })

        self.aml_commercial_ad = self.env['account.move.line'].create({
            'product_id': self.product_a.id,
            'price_unit': 1000.0,
            'analytic_distribution': {
                self.commercial_aa.id: 100,
            },
            'move_id': self.move.id
        })

        self.aml_com_marketing_ad = self.env['account.move.line'].create({
            'product_id': self.product_a.id,
            'price_unit': 1000.0,
            'analytic_distribution': {
                self.com_marketing_aa.id: 100,
            },
            'move_id': self.move.id
        })

        self.aml_without_ad = self.env['account.move.line'].create({
            'product_id': self.product_a.id,
            'price_unit': 100.0,
            'move_id': self.move.id
        })

        self.aml_without_ad_1 = self.env['account.move.line'].create({
            'product_id': self.product_a.id,
            'price_unit': 100.0,
            'move_id': self.move.id
        })

        def filter_domain(comparator, value):
            return self.move.invoice_line_ids.filtered_domain([('analytic_distribution', comparator, value)])

        self.assertEqual(filter_domain('=', 'Research & Development'), self.aml_rd_ad)
        self.assertEqual(filter_domain('=', 'Sales'), self.aml_sales_admin_ad)
        self.assertEqual(filter_domain('=', 'Administrative'), self.aml_sales_admin_ad)
        self.assertEqual(filter_domain('=', 'Commercial'), self.aml_commercial_ad)
        self.assertFalse(filter_domain('=', ''))  # Should returns an empty recordset
        self.assertEqual(filter_domain('=', self.commercial_aa.id), self.aml_commercial_ad)

        self.assertEqual(filter_domain('ilike', 'Commercial'), self.aml_commercial_ad | self.aml_com_marketing_ad)
        self.assertEqual(filter_domain('ilike', ''), self.move.invoice_line_ids - self.aml_without_ad - self.aml_without_ad_1)

        self.assertEqual(filter_domain('not ilike', 'Commercial'), self.move.invoice_line_ids - self.aml_com_marketing_ad - self.aml_commercial_ad)
        self.assertEqual(filter_domain('not ilike', ''), self.aml_without_ad + self.aml_without_ad_1)  # Should returns an AML without analytic_distribution

        self.assertEqual(filter_domain('!=', 'Commercial & Marketing'), self.move.invoice_line_ids - self.aml_com_marketing_ad)
        self.assertEqual(filter_domain('!=', ''), self.move.invoice_line_ids)  # Should returns an every AML
        self.assertEqual(filter_domain('!=', self.commercial_aa.id), self.move.invoice_line_ids - self.aml_commercial_ad)

        self.assertEqual(filter_domain('in', [self.commercial_aa.id]), self.aml_commercial_ad)
        self.assertEqual(filter_domain('in', (self.sales_aa + self.rd_aa).ids), self.aml_sales_admin_ad + self.aml_rd_ad)
