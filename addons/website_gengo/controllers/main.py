# -*- coding: utf-8 -*-

from openerp import http
from openerp.http import request

GENGO_DEFAULT_LIMIT = 20


class WebsiteGengo(http.Controller):

    @http.route('/website/get_translated_length', type='json', auth='user', website=True)
    def get_translated_length(self, translated_ids, lang):
        result = {"done": 0}
        gengo_translations = request.env['ir.translation'].search([('id', 'in', translated_ids), ('gengo_translation', '!=', False)])
        for trans in gengo_translations:
            result['done'] += len(trans.source.split())
        return result

    @http.route('/website/check_gengo_set', type='json', auth='user', website=True)
    def check_gengo_set(self):
        company_flag = 0
        user = request.env.user.sudo()
        if not user.company_id.gengo_public_key or not user.company_id.gengo_private_key:
            company_flag = user.company_id.id
        return company_flag

    @http.route('/website/set_gengo_config', type='json', auth='user', website=True)
    def set_gengo_config(self, config):
        return request.env.user.company_id.write(config)

    @http.route('/website/post_gengo_jobs', type='json', auth='user', website=True)
    def post_gengo_jobs(self):
        request.env['base.gengo.translations']._sync_request(
            limit=GENGO_DEFAULT_LIMIT)
        return True
