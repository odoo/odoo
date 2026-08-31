# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestStockReportTour(HttpCase):

    def _get_report_url(self):
        return '/odoo/action-stock.product_template_action_product'

    def test_stock_route_diagram_report(self):
        """ Open the route diagram report."""
        # Do not make the test rely on demo data
        self.env['product.template'].search([('type', '!=', 'service')]).action_archive()
        # Create variant products for variant/warehouse routes selection
        self.env.ref('base.group_user').write({'implied_ids': [(4, self.env.ref('product.group_product_variant').id)]})
        product_attribute = self.env['product.attribute'].create({
            'name': 'PA',
            'create_variant': 'always'
        })
        self.env['product.attribute.value'].create([{
            'name': 'PAV' + str(i),
            'attribute_id': product_attribute.id
        } for i in range(2)])
        product = self.env['product.template'].create({
            'name': 'Test Storable Product',
            'is_storable': True,
        })
        self.env['product.template.attribute.line'].create({
            'attribute_id': product_attribute.id,
            'product_tmpl_id': product.id,
            'value_ids': [(6, 0, product_attribute.value_ids.ids)],
        })
        url = self._get_report_url()

        self.start_tour(url, 'test_stock_route_diagram_report', login='admin', timeout=180)

    def test_context_from_warehouse_filter(self):
        """
        Check that the warehouse context key added from the product search warehouse filter
        is correctly parsed when used.
        """
        self.env['product.product'].create({
            'name': 'Lovely Product',
            'is_storable': True,
            'is_favorite': True,
        })
        self.env['stock.warehouse'].create({
            'name': 'Warehouse A',
            'code': 'WH-A',
            'company_id': self.env.user.company_id.id,
        })
        self.env['stock.warehouse'].create({
            'name': 'Warehouse B',
            'code': 'WH-B',
            'company_id': self.env.user.company_id.id,
        })

        self.start_tour(self._get_report_url(), 'test_context_from_warehouse_filter', login='admin', timeout=180)
