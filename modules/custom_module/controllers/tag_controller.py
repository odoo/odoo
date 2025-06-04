from odoo import http, _
from odoo.exceptions import UserError
from odoo.http import request, Response
import json
from ..cors_module.cors_controllers import CorsController
import logging
import requests
_logger = logging.getLogger(__name__)


class TagController(http.Controller):

    @http.route('/create_tag', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    def create_tag(self):
        print('Entering create_tag method')
        if request.httprequest.method == 'OPTIONS':
            return CorsController._add_cors_headers(Response(status=204))

        try:
            data = request.httprequest.data.decode('utf-8')
            print(f"Received data: {data}")
            if data:
                data = json.loads(data)
            else:
                return {'error': 'No data provided'}

            name = data.get('name')
            menupro_id = data.get('menupro_id')
            status = data.get('status')

            print(f"Name: {name}, MenuPro ID: {menupro_id}, Status: {status}")

            if not name:
                missing_fields = []
                if not name: missing_fields.append('name')
                response = {'error': f'Missing required fields: {", ".join(missing_fields)}'}
                return CorsController._add_cors_headers(
                    Response(json.dumps(response), content_type='application/json', status=400))

            odoo_data = {
                'name': name
            }

            created_tag = request.env['table.tags'].sudo().create(odoo_data)
            if not created_tag:
                response = {'error': 'Error while creating tag in Odoo'}
                return CorsController._add_cors_headers(
                    Response(json.dumps(response), content_type='application/json', status=500))

            mp_data = {
                'name': name,
                'odooId': created_tag.id
            }
            print(f"Sending PATCH request to MenuPro: {mp_data}")
            mp_response = requests.patch(f'https://api.menupro.tn/tags/{menupro_id}', json=mp_data)
            print(f"MenuPro response status: {mp_response.status_code}")
            print(f"MenuPro response content: {mp_response.content}")

            response = {'status': 'Tag created successfully', 'id': created_tag.id}
            return CorsController._add_cors_headers(
                Response(json.dumps(response), content_type='application/json', status=200))

        except Exception as e:
            print(f"Error in create_tag: {str(e)}")
            response = {'error': str(e)}
            return CorsController._add_cors_headers(
                Response(json.dumps(response), content_type='application/json', status=500))

    @http.route('/delete_tag', type='http', auth='public', methods=['DELETE', 'OPTIONS'], csrf=False)
    def delete_tag(self):

        if request.httprequest.method == 'OPTIONS':
            return CorsController._add_cors_headers(Response(status=204))

        tag_id = request.params.get('tag_id')
        if not tag_id:
            response = {'error': 'Missing tag_id'}
            return CorsController._add_cors_headers(
                Response(json.dumps(response), content_type='application/json', status=400))

        try:
            # Search for the tag in Odoo
            tag = request.env['table.tags'].sudo().search([('id', '=', tag_id)], limit=1)
            menupro_id=tag.menupro_id
            print('menupro id',menupro_id)
            if not tag:
                response = {'error': 'Tag not found'}
                return CorsController._add_cors_headers(
                    Response(json.dumps(response), content_type='application/json', status=404))

            # Step 1: Send DELETE request to MenuPro API
            print(f"Attempting to delete tag from MenuPro with ID: {tag_id}")
            mp_response = requests.delete(f"https://api.menupro.tn/tags/{menupro_id}")
            print(f"MenuPro delete response status: {mp_response.status_code}")
            print(f"MenuPro delete response content: {mp_response.content}")

            # Check the response status code
            if not mp_response.status_code in [200, 204]:
                raise UserError(_("Failed to delete tag from MenuPro: %s") % mp_response.text)

            # Step 2: Delete tag in Odoo
            tag.unlink()

            response = {'status': 'Tag deleted successfully'}
            return CorsController._add_cors_headers(
                Response(json.dumps(response), content_type='application/json', status=200))

        except Exception as e:
            print(f"Error in delete_tag: {str(e)}")
            response = {'error': str(e)}
            return CorsController._add_cors_headers(
                Response(json.dumps(response), content_type='application/json', status=500))

    @http.route('/validate_private', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def update_tag_status(self, **kwargs):
        tag_id = kwargs.get('tag_id')
        if not tag_id:
            return {'error': 'Missing tag_id'}

        try:
            tag = request.env['table.tags'].sudo().search([('id', '=', tag_id)], limit=1)
            if not tag:
                return {'error': 'Tag not found'}

            # Update the status to 'PRIVATE'
            tag.sudo().write({'status': 'PRIVATE'})
            return {'status': 'Tag updated to PRIVATE successfully'}

        except Exception as e:
            return {'error': str(e)}
