# Part of GPCB. See LICENSE file for full copyright and licensing details.

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

API_PREFIX = '/api/v1'


class GpcbApiProduct(http.Controller):

    # ------------------------------------------------------------------
    # GET /api/v1/products — List/search products
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/products',
        type='http', auth='bearer', methods=['GET'],
        csrf=False, save_session=False, readonly=True,
    )
    def list_products(self, **kw):
        """List/search products with tax information."""
        limit = min(int(kw.get('limit', 40)), 200)
        offset = int(kw.get('offset', 0))

        domain = [('sale_ok', '=', True)]
        if kw.get('search'):
            domain = [
                '|', '|',
                ('name', 'ilike', kw['search']),
                ('default_code', 'ilike', kw['search']),
                ('barcode', '=', kw['search']),
            ] + domain
        if kw.get('category'):
            domain.append(('categ_id.name', 'ilike', kw['category']))
        if kw.get('code'):
            domain.append(('default_code', '=', kw['code']))
        if kw.get('barcode'):
            domain.append(('barcode', '=', kw['barcode']))

        products = request.env['product.product'].search(
            domain, limit=limit, offset=offset, order='name',
        )
        total = request.env['product.product'].search_count(domain)

        return request.make_json_response({
            'status': 'success',
            'data': {
                'items': [self._serialize_product(p) for p in products],
                'total': total,
                'limit': limit,
                'offset': offset,
            },
        })

    # ------------------------------------------------------------------
    # GET /api/v1/products/:id — Product detail
    # ------------------------------------------------------------------
    @http.route(
        f'{API_PREFIX}/products/<int:product_id>',
        type='http', auth='bearer', methods=['GET'],
        csrf=False, save_session=False, readonly=True,
    )
    def get_product(self, product_id, **kw):
        """Retrieve product detail with default taxes."""
        product = request.env['product.product'].browse(product_id).exists()
        if not product:
            return request.make_json_response(
                {'status': 'error', 'message': 'Product not found'}, status=404,
            )
        return request.make_json_response({
            'status': 'success',
            'data': self._serialize_product(product),
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _serialize_product(self, product):
        """Serialize a product to a JSON-safe dict."""
        return {
            'id': product.id,
            'name': product.name,
            'code': product.default_code or '',
            'barcode': product.barcode or '',
            'type': product.type,
            'list_price': product.list_price,
            'standard_price': product.standard_price,
            'category': product.categ_id.name or '',
            'uom': product.uom_id.name or '',
            'sale_ok': product.sale_ok,
            'purchase_ok': product.purchase_ok,
            'taxes_id': [
                {'id': t.id, 'name': t.name, 'amount': t.amount, 'type': t.amount_type}
                for t in product.taxes_id
            ],
            'supplier_taxes_id': [
                {'id': t.id, 'name': t.name, 'amount': t.amount, 'type': t.amount_type}
                for t in product.supplier_taxes_id
            ],
        }
