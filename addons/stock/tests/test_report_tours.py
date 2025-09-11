# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestStockReportTour(HttpCase):

    def _get_report_url(self):
        return '/odoo/action-stock.product_template_action_product'

    def test_stock_route_diagram_report(self):
        """ Open the route diagram report."""
        # Do not make the test rely on demo data
        self.env.ref('stock.route_warehouse0_mto').active = True
        self.env['product.template'].search([('type', '!=', 'service')]).write({'active': False})
        self.env['product.template'].create({
            'name': 'Test Storable Product',
            'is_storable': True,
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

    def test_forecast_replenishment(self):
        """
        Test repenish from the forecast page.
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        interdimensional_protal = self.env['stock.location'].create({
            'name': 'Interdimensional portal',
            'usage': 'internal',
            'location_id': warehouse.lot_stock_id.id,
        })
        lovely_route = self.env['stock.route'].create({
            'name': 'Lovely Route',
            'product_selectable': True,
            'product_categ_selectable': True,
            'sequence': 1,
            'rule_ids': [Command.create({
                'name': 'Interdimensional portal -> Stock',
                'action': 'pull',
                'picking_type_id': self.ref('stock.picking_type_internal'),
                'location_src_id': interdimensional_protal.id,
                'location_dest_id':  warehouse.lot_stock_id.id,
            })],
        })
        self.env['product.template'].create({
            'name': 'Lovely Product',
            'is_storable': True,
            'is_favorite': True,
            'route_ids': [Command.link(lovely_route.id)],
        })
        self.start_tour(self._get_report_url(), 'test_forecast_replenishment', login='admin', timeout=180)
