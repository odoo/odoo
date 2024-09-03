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

    def test_multiple_warehouses_filter(self):

        self.env['product.product'].create({
            'name': 'Product A',
            'default_code': 'PA',
            'lst_price': 100.0,
            'standard_price': 100.0,
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

        self.start_tour(self._get_report_url(), 'test_multiple_warehouses_filter', login='admin', timeout=180)
