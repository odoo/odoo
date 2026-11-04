
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestDropshipAnalyticDistribution(ValuationReconciliationTestCommon):
    """ a dropship move is linked to both a purchase line and a sale line, so we
        shouldn't stack both sides' analytic distributions on top of each other on the stock
        valuation entry.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.anglo_saxon_accounting = True

        cls.dropshipping_route = cls.env.ref('stock_dropshipping.route_drop_shipping')
        cls.vendor = cls.env['res.partner'].create({'name': 'Partner A'})
        cls.customer = cls.env['res.partner'].create({'name': 'Partner B'})

        cls.vendor_plan = cls.env['account.analytic.plan'].create({'name': 'Vendor Plan'})
        cls.vendor_account = cls.env['account.analytic.account'].create({
            'name': 'AA of Vendor ADM',
            'plan_id': cls.vendor_plan.id,
        })
        cls.env['account.analytic.distribution.model'].create({
            'partner_id': cls.vendor.id,
            'analytic_distribution': {cls.vendor_account.id: 100},
            'company_id': cls.env.company.id,
        })

        # A second ADM matched on the customer, so the sale order line also ends up with its
        # own analytic distribution (this is what a project would normally add, but we don't
        # need the project app to trigger the bug: any distribution on the sale line is enough).
        cls.customer_plan = cls.env['account.analytic.plan'].create({'name': 'Customer Plan'})
        cls.customer_account = cls.env['account.analytic.account'].create({
            'name': 'AA of Customer ADM',
            'plan_id': cls.customer_plan.id,
        })
        cls.env['account.analytic.distribution.model'].create({
            'partner_id': cls.customer.id,
            'analytic_distribution': {cls.customer_account.id: 100},
            'company_id': cls.env.company.id,
        })

        cls.product = cls.env['product.product'].create({
            'name': 'Large Desk',
            'is_storable': True,
            'categ_id': cls.stock_account_product_categ.id,
            'taxes_id': [(6, 0, [])],
            'route_ids': [(6, 0, [cls.dropshipping_route.id])],
            'seller_ids': [(0, 0, {'partner_id': cls.vendor.id, 'price': 8})],
        })
        cls.product.product_tmpl_id.categ_id.property_cost_method = 'standard'
        cls.product.product_tmpl_id.standard_price = 10
        cls.product.product_tmpl_id.categ_id.property_valuation = 'real_time'
        cls.product.product_tmpl_id.invoice_policy = 'order'

    def test_dropship_valuation_entry_analytic_distribution_not_doubled(self):
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'partner_invoice_id': self.customer.id,
            'partner_shipping_id': self.customer.id,
            'order_line': [(0, 0, {
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'product_uom': self.product.uom_id.id,
                'price_unit': 12,
                'tax_id': [(6, 0, [])],
            })],
            'picking_policy': 'direct',
        })
        so.action_confirm()

        po = self.env['purchase.order'].search([('group_id', '=', so.procurement_group_id.id)])
        po.button_confirm()
        so.picking_ids.button_validate()

        expected_distribution = {str(self.vendor_account.id): 100.0}
        valuation_lines = so.picking_ids.move_ids.account_move_ids.line_ids.filtered('analytic_distribution')
        self.assertTrue(valuation_lines, "the dropship valuation entry should have an analytic distribution")
        for line in valuation_lines:
            self.assertEqual(
                line.analytic_distribution, expected_distribution,
                "the vendor's ADM (purchase side) should be the only one applied here, not stacked on top of "
                "the customer's ADM (sale side) too"
            )
