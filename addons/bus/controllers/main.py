# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.http import Controller, request, route


class BusController(Controller):
    @route('/bus/im_status', type="json", auth="user")
    def im_status(self, partner_ids):
        return {
            'partners': request.env['res.partner'].with_context(active_test=False).search([('id', 'in', partner_ids)]).read(['im_status'])
        }

    @route('/bus/get_model_definitions', methods=['POST'], type='http', auth='user')
    def get_model_definitions(self, model_names_to_fetch, **kwargs):
        return request.make_response(json.dumps(
            request.env['ir.model']._get_model_definitions(json.loads(model_names_to_fetch)),
        ))
