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
    
   
    @http.route('/api/add_products', type='json', auth='user', methods=['POST'])
    def add_products_api(self, **post):
        try:
            Product = request.env['product.product']
            StockChangeProductQty = request.env['stock.change.product.qty']
            products_data = post.get('products')
            print(products_data)  # Print the products data

            if not products_data:
                return Response(json.dumps({'error': 'No products provided'}), status=400, content_type='application/json')

            created_products = []
            for product_data in products_data:
                logger.info(f"Product data: {product_data}")

                required_fields = {
                    'name': product_data.get('name'),
                    'detailed_type': product_data.get('detailed_type', 'product'),  # Default type if not provided
                    'list_price': product_data.get('list_price'),
                    'categ_id': product_data.get('categ_id'),  # Assuming categ_id is the category ID
                    'default_code': product_data.get('default_code', '')
                }

                # Check if all required fields are provided
                missing_fields = [key for key, value in required_fields.items() if value is None]
                if missing_fields:
                    return Response(
                        json.dumps({'error': f'Missing required fields: {", ".join(missing_fields)}'}),
                        status=400,
                        content_type='application/json'
                    )

                # Create the product with required fields
                new_product = Product.create(required_fields)

                # Get the new quantity from the API call
                new_quantity = product_data.get('new_quantity')
                if new_quantity is not None:
                    # Create stock change with both product_id and product_tmpl_id
                    stock_change = StockChangeProductQty.create({
                        'product_id': new_product.id,
                        'product_tmpl_id': new_product.product_tmpl_id.id,  # Use product_tmpl_id
                        'new_quantity': new_quantity,
                    })
                    stock_change.change_product_qty()

                # Append created product details to response
                created_products.append({
                    'id': new_product.id,
                    'name': new_product.name,
                    'default_code': new_product.default_code,
                    'list_price': new_product.list_price,
                    'qty_available': new_product.qty_available,
                })

            return Response(json.dumps({'success': True, 'products': created_products}), content_type='application/json')

        except Exception as e:
            logger.error(f"Error adding products via API: {e}")
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')