# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo
from odoo.tests import Form, HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestStockReportTour(HttpCase):

    def _get_report_url(self):
        return '/web#&model=product.template&action=stock.product_template_action_product'

    def test_stock_route_diagram_report(self):
        """ Open the route diagram report."""
        url = self._get_report_url()

        self.start_tour(url, 'test_stock_route_diagram_report', login='admin', timeout=180)

    def test_context_from_warehouse_filter(self):
        """
        Check that the warehouse context key added from the product search warehouse filter
        is correctly parsed when used. 
        """
        self.env['product.product'].create({
            'name': 'Lovely Product',
            'type': 'product'
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
