# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo.tests import HttpCase

from odoo.addons.point_of_sale.tests.test_pos_accounting import TestPosAccounting


class TestPosAccountingHttp(HttpCase, TestPosAccounting):
    def _get_url(self, pos_config=None):
        pos_config = pos_config or self.pos_config
        return f"/pos/ui/{pos_config.id}"

    def start_pos_tour(self, tour_name, **kwargs):
        self.start_tour(self._get_url(pos_config=kwargs.get('pos_config')), tour_name, login=self.env.user.login, **kwargs)

    def test_baseline_between_frontend_and_backend(self):
        company = self.pos_config.company_id
        company.tax_calculation_rounding_method = 'round_globally'

        only_categ = self.env['pos.category'].create(
            {'name': 'Only Category'},
        )
        self.pos_config.write({
            'limit_categories': True,
            'iface_available_categ_ids': [(6, 0, [only_categ.id])],
        })
        tax_16 = self.env['account.tax'].create({
            'name': 'Tax 16%',
            'amount': 16,
        })
        self.env['product.product'].create([{
            'name': 'Test Product 1',
            'list_price': 7051.73,
            'pos_categ_ids': [(6, 0, [only_categ.id])],
            'taxes_id': [(6, 0, [tax_16.id])],
            'available_in_pos': True,
        }, {
            'name': 'Test Product 2',
            'list_price': 352.59,
            'pos_categ_ids': [(6, 0, [only_categ.id])],
            'taxes_id': [(6, 0, [tax_16.id])],
            'available_in_pos': True,
        }])

        def get_frontend_data(self, frontend_data):
            frontend_data = json.loads(frontend_data)
            base_lines = self.lines._prepare_base_lines_for_taxes_computation()
            zipped = zip(frontend_data['baseLines'], base_lines)
            for frontend_line, backend_line in zipped:
                if frontend_line.get('is_refund', False) != backend_line['is_refund']:
                    error = "Refund status mismatch between frontend and backend"
                    raise ValueError(error)

                if frontend_line.get('quantity', 0) != backend_line['quantity']:
                    error = "Quantity mismatch between frontend and backend"
                    raise ValueError(error)

                if frontend_line.get('sign') != backend_line['sign']:
                    error = "Sign mismatch between frontend and backend"
                    raise ValueError(error)

        # Add function to model
        order_model = self.env.registry.models['pos.order']
        order_model.get_frontend_data = get_frontend_data

        self.open_pos_session()
        self.start_pos_tour('test_baseline_between_frontend_and_backend')
