import json
import logging

from odoo import http
from odoo.http import request, Response
import pdb; 
logger = logging.getLogger(__name__)

class ProductInventoryController(http.Controller):

    @http.route('/product/inventory/page', type='http', auth='user', website=True)
    def product_inventory_page(self):
        products = request.env['product.product'].search([])
        product_list = []
        for product in products:
            product_list.append({
                'id': product.id,
                'name': product.name,
                'default_code': product.default_code,
                'list_price': product.list_price,
                'qty_available': product.qty_available,
            })

        logger.info("Rendering the product inventory page")
        return request.render('ash_product_inventory.product_inventory_template', {'products': product_list})

    @http.route('/api/product/inventory', type='http', auth='user', methods=['GET'], csrf=False)
    def product_inventory_api(self):
        products = request.env['product.product'].search([])
        product_list = []
        for product in products:
            product_list.append({
                'id': product.id,
                'name': product.name,
                'default_code': product.default_code,
                'list_price': product.list_price,
                'qty_available': product.qty_available,
            })

        return request.make_response(json.dumps(product_list), headers=[('Content-Type', 'application/json')])
    


    @http.route('/api/test2', type='json', auth='user', methods=['POST'])
    def add_or_update_products(self, **post):
        try:
            Product = request.env['product.product']
            StockChangeProductQty = request.env['stock.change.product.qty']
            products_data = post.get('products')

            if not products_data:
                return Response(json.dumps({'error': 'No products provided'}), status=400, content_type='application/json')

            updated_products = []
            for product_data in products_data:
                logger.info(f"Product data: {product_data}")

                # Check if a product with the same default_code already exists
                existing_product = Product.search([('default_code', '=', product_data.get('default_code'))], limit=1)

                if existing_product:
                    # Update the existing product with new data
                    existing_product.write({
                        'name': product_data.get('name'),
                        'detailed_type': product_data.get('detailed_type', 'product'),  # Default type if not provided
                        'list_price': product_data.get('list_price'),
                        'categ_id': product_data.get('categ_id'),
                        'sku': product_data.get('sku', ''),
                        'outer_gtin': product_data.get('outer_gtin', ''),
                        'brand': product_data.get('brand', ''),
                        'source': product_data.get('source', ''),
                        'pack_size_pcs': product_data.get('pack_size_pcs', 0),
                        'carton_length': product_data.get('carton_length', ''),
                        'carton_width': product_data.get('carton_width', ''),
                        'carton_height': product_data.get('carton_height', ''),
                        'product_length': product_data.get('product_length', ''),
                        'product_width': product_data.get('product_width', ''),
                        'product_height': product_data.get('product_height', ''),
                        'image_url': product_data.get('image_url', ''),
                        'volume': product_data.get('volume'),
                        'weight': product_data.get('weight'),
                    })
                    updated_products.append({
                        'id': existing_product.id,
                        'name': existing_product.name,
                        'default_code': existing_product.default_code,
                        'list_price': existing_product.list_price,
                        'qty_available': existing_product.qty_available,
                    })
                else:
                    # Create a new product if it doesn't exist
                    new_product = Product.create({
                        'name': product_data.get('name'),
                        'detailed_type': product_data.get('detailed_type', 'product'),  # Default type if not provided
                        'list_price': product_data.get('list_price'),
                        'categ_id': product_data.get('categ_id'),
                        'default_code': product_data.get('default_code', ''),
                        'sku': product_data.get('sku', ''),
                        'outer_gtin': product_data.get('outer_gtin', ''),
                        'brand': product_data.get('brand', ''),
                        'source': product_data.get('source', ''),
                        'pack_size_pcs': product_data.get('pack_size_pcs', 0),
                        'carton_length': product_data.get('carton_length', ''),
                        'carton_width': product_data.get('carton_width', ''),
                        'carton_height': product_data.get('carton_height', ''),
                        'product_length': product_data.get('product_length', ''),
                        'product_width': product_data.get('product_width', ''),
                        'product_height': product_data.get('product_height', ''),
                        'image_url': product_data.get('image_url', ''),
                        'volume': product_data.get('volume'),
                        'weight': product_data.get('weight'),
                    })

                    # Handle stock quantity if provided
                    new_quantity = product_data.get('new_quantity')
                    if new_quantity is not None:
                        stock_change = StockChangeProductQty.create({
                            'product_id': new_product.id,
                            'product_tmpl_id': new_product.product_tmpl_id.id,
                            'new_quantity': new_quantity,
                        })
                        stock_change.change_product_qty()

                    updated_products.append({
                        'id': new_product.id,
                        'name': new_product.name,
                        'default_code': new_product.default_code,
                        'list_price': new_product.list_price,
                        'qty_available': new_product.qty_available,
                    })

            return Response(json.dumps({'success': True, 'products': updated_products}), content_type='application/json')

        except Exception as e:
            logger.error(f"Error adding or updating products via API: {e}")
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')
