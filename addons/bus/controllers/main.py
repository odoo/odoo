# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.http import Controller, request, route


class BusController(Controller):
    @route('/bus/get_test_data', methods=['POST'], type='http', auth='user')
    def get_test_data(self, model_names_to_fetch, refs_to_fetch):
        model_definitions = request.env['ir.model']._get_model_definitions(json.loads(model_names_to_fetch))
        records_by_model_name, unreachable_refs = request.env['ir.model']._get_records_by_model_name(
            model_definitions, json.loads(refs_to_fetch)
        )
        current_user = request.env.user.read([
            fname for fname, field in model_definitions['res.users'].items() if field['type'] != 'binary'
        ], load=None)[0]
        current_partner = request.env.user.partner_id.read([
            fname for fname, field in model_definitions['res.partner'].items() if field['type'] != 'binary'
        ], load=None)[0]
        return json.dumps({
            'current_partner': current_partner,
            'current_user': current_user,
            'model_definitions': model_definitions,
            'records_by_model_name': records_by_model_name,
            'unreachable_refs': unreachable_refs,
        }, default=str)
