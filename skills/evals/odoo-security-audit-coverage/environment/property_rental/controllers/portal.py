import ast
import base64
import json
import os
import pickle

from werkzeug.exceptions import Forbidden, NotFound

from odoo import http
from odoo.http import request
from odoo.tools import consteq

CONTRACTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'contracts')


class RentalPortal(http.Controller):

    def _get_own_lease(self, lease_id):
        lease = request.env['rental.lease'].search([
            ('id', '=', lease_id),
            ('tenant_id', '=', request.env.user.partner_id.id),
        ])
        if not lease:
            raise NotFound()
        return lease

    @http.route('/my/leases', type='http', auth='user')
    def portal_my_leases(self, **kw):
        domain = [('tenant_id', '=', request.env.user.partner_id.id)]
        if kw.get('filter'):
            domain = ast.literal_eval(kw['filter']) + domain
        leases = request.env['rental.lease'].sudo().search(domain)
        if kw.get('rule'):
            leases = leases._filtered_by_rule(kw['rule'])
        return request.render('property_rental.portal_my_leases', {'leases': leases})

    @http.route('/my/leases/<int:lease_id>/cancel', type='http', auth='user')
    def portal_lease_cancel(self, lease_id, **kw):
        lease = self._get_own_lease(lease_id)
        lease.sudo().state = 'cancelled'
        return request.redirect('/my/leases')

    @http.route('/my/leases/<int:lease_id>/update', type='http', auth='user', methods=['POST'], csrf=False)
    def portal_lease_update(self, lease_id, **post):
        lease = self._get_own_lease(lease_id)
        lease.sudo().write(post)
        return request.redirect('/my/leases')

    @http.route('/my/leases/<int:lease_id>/value', type='jsonrpc', auth='user')
    def portal_lease_value(self, lease_id, field):
        lease = self._get_own_lease(lease_id)
        return str(getattr(lease, field))

    @http.route('/rental/record', type='jsonrpc', auth='user')
    def rental_record(self, model, res_id, fields):
        return request.env[model].sudo().browse(int(res_id)).read(fields)

    @http.route('/rental/properties', type='jsonrpc', auth='public')
    def rental_properties(self):
        return request.env['rental.property'].sudo().search_read(
            [], ['name', 'rent_amount', 'owner_id', 'owner_bank_account'],
        )

    @http.route('/rental/lease/sign', type='jsonrpc', auth='public')
    def rental_lease_sign(self, lease_id, token, user_id):
        lease = request.env['rental.lease'].sudo().browse(int(lease_id)).exists()
        if not lease or not lease.check_access_token(token):
            raise Forbidden()
        lease.with_user(int(user_id)).action_sign()
        return True

    @http.route('/rental/contract', type='http', auth='user')
    def rental_contract(self, name):
        with open(os.path.join(CONTRACTS_DIR, name), 'rb') as contract:
            content = contract.read()
        return request.make_response(content, [('Content-Type', 'application/pdf')])

    @http.route('/rental/listing/sync', type='http', auth='public', methods=['POST'], csrf=False)
    def rental_listing_sync(self, property_id, token, payload):
        prop = request.env['rental.property'].sudo().browse(int(property_id)).exists()
        if not prop or not prop.listing_api_token or not consteq(token, prop.listing_api_token):
            raise Forbidden()
        listing = pickle.loads(base64.b64decode(payload))
        prop.rent_amount = float(listing['rent'])
        return request.make_response(json.dumps({'ok': True}), [('Content-Type', 'application/json')])
