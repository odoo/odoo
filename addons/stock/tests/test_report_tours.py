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
        self.env['product.template'].create({
            'name': 'Test Storable Product',
            'is_storable': True,
        })
        url = self._get_report_url()

        self.start_tour(url, 'test_stock_route_diagram_report', login='admin', timeout=180)
