# Part of GPCB. See LICENSE file for full copyright and licensing details.

import logging

from odoo import http
from odoo.http import request
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

API_PREFIX = '/api/v1'


class GpcbApiTax(http.Controller):

    # ------------------------------------------------------------------
    # POST /api/v1/tax/compute — Preview tax computation
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/tax/compute',
        type='http', auth='bearer', methods=['POST'],
        csrf=False, save_session=False, readonly=True,
    )
    def compute_taxes(self, **kw):
        """Preview tax computation for a set of lines.

        Expected body::

            {
              "partner_id": 42,
              "lines": [
                {"product_id": 10, "quantity": 1, "unit_price": 85000},
                {"product_id": 20, "quantity": 2, "unit_price": 50000}
              ],
              "currency_id": 170
            }
        """
        try:
            data = request.get_json_data()
            if not data or not data.get('lines'):
                return request.make_json_response(
                    {'status': 'error', 'message': 'Lines are required'}, status=400,
                )

            # Resolve partner for fiscal position
            partner = None
            if data.get('partner_id'):
                partner = request.env['res.partner'].browse(
                    int(data['partner_id'])
                ).exists()

            fiscal_position = None
            if partner:
                fiscal_position = request.env['account.fiscal.position']._get_fiscal_position(
                    partner,
                )

            currency = request.env.company.currency_id
            if data.get('currency_id'):
                currency = request.env['res.currency'].browse(
                    int(data['currency_id'])
                ).exists() or currency

            results = []
            total_untaxed = 0
            total_tax = 0

            for line in data['lines']:
                quantity = line.get('quantity', 1)
                unit_price = line.get('unit_price', 0)

                # Resolve taxes
                taxes = request.env['account.tax']
                if line.get('tax_ids'):
                    taxes = request.env['account.tax'].browse(
                        [int(t) for t in line['tax_ids'] if str(t).isdigit()]
                    ).exists()
                elif line.get('product_id'):
                    product = request.env['product.product'].browse(
                        int(line['product_id'])
                    ).exists()
                    if product:
                        taxes = product.taxes_id

                # Apply fiscal position
                if fiscal_position and taxes:
                    taxes = fiscal_position.map_tax(taxes)

                # Compute
                tax_result = taxes.compute_all(
                    unit_price, currency=currency, quantity=quantity,
                    partner=partner,
                )

                line_result = {
                    'product_id': line.get('product_id'),
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'subtotal': tax_result['total_excluded'],
                    'total': tax_result['total_included'],
                    'taxes': [
                        {
                            'id': t['id'],
                            'name': t['name'],
                            'amount': t['amount'],
                            'base': t['base'],
                        }
                        for t in tax_result['taxes']
                    ],
                }
                results.append(line_result)
                total_untaxed += tax_result['total_excluded']
                total_tax += sum(t['amount'] for t in tax_result['taxes'])

            return request.make_json_response({
                'status': 'success',
                'data': {
                    'lines': results,
                    'total_untaxed': total_untaxed,
                    'total_tax': total_tax,
                    'total': total_untaxed + total_tax,
                    'currency': currency.name,
                },
            })

        except (UserError, ValueError) as e:
            return request.make_json_response(
                {'status': 'error', 'message': str(e)}, status=400,
            )
