# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestAnalyticAccount(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The group 'mrp.group_mrp_routings' is required to make the field
        # 'workorder_ids' visible in the view of 'mrp.production'. The subviews
        #  of `workorder_ids` must be present in many tests to create records.
        cls.env.user.group_ids += (
            cls.env.ref('analytic.group_analytic_accounting')
            + cls.env.ref('mrp.group_mrp_routings')
        )

        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Plan',
        })
        cls.applicability = cls.env['account.analytic.applicability'].create({
            'business_domain': 'general',
            'analytic_plan_id': cls.analytic_plan.id,
            'applicability': 'mandatory',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Product',
            'is_storable': True,
            'standard_price': 233.0,
        })

    def test_mandatory_analytic_plan_bom(self):
        """
        Tests that the distribution validation is correctly evaluated
        The BOM creation should not be constrained by any analytic applicability rule.
        """
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product.product_tmpl_id.id,
        })
        self.assertTrue(bom)

        self.applicability.business_domain = 'manufacturing_order'

        bom_2 = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product.product_tmpl_id.id,
        })
        self.assertTrue(bom_2)

    def test_mandatory_analytic_plan_workcenter(self):
        """
        Tests that the distribution validation is correctly evaluated
        The Workcenter creation should not be constrained by any analytic applicability rule.
        """
        workcenter = self.env['mrp.workcenter'].create({
            'name': "Great Workcenter",
            'analytic_distribution': False,
        })
        self.assertTrue(workcenter)

        self.applicability.business_domain = 'manufacturing_order'

        workcenter_2 = self.env['mrp.workcenter'].create({
            'name': "Great Workcenter",
            'analytic_distribution': False,
        })
        self.assertTrue(workcenter_2)
