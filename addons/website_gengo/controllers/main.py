# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request

GENGO_DEFAULT_LIMIT = 20


class WebsiteGengo(http.Controller):

    @http.route('/website/get_translated_length', type='json', auth='user', website=True)
    def get_translated_length(self, translated_ids, lang):
        result = {"done": 0}
        gengo_translation_ids = request.env['ir.translation'].search([('id', 'in', translated_ids), ('gengo_translation', '!=', False)])
        for trans in gengo_translation_ids:
            result['done'] += len(trans.source.split())
        return result

    @http.route('/website/check_gengo_set', type='json', auth='user', website=True)
    def check_gengo_set(self):
        company = request.env.user.sudo().company_id
        company_flag = 0
        if not company.gengo_public_key or not company.gengo_private_key:
            company_flag = company.id
        return company_flag

    @http.route('/website/set_gengo_config', type='json', auth='user', website=True)
    def set_gengo_config(self, config):
        request.env.user.company_id.write(config)
        return True

    @http.route('/website/post_gengo_jobs', type='json', auth='user', website=True)
    def post_gengo_jobs(self):
        request.env['base.gengo.translations']._sync_request(limit=GENGO_DEFAULT_LIMIT)
        return True

    @http.route('/website_gengo/set_translations', type='json', auth='user', website=True)
    def set_translations(self, data, lang):
        IrTranslation = request.env['ir.translation']
        for term in data:
            initial_content = term['initial_content'].strip()
            translation_ids = term['translation_id']
            if not translation_ids:
                translations = IrTranslation.search_read([('lang', '=', lang), ('src', '=', initial_content)], fields=['id'])
                if translations:
                    translation_ids = [t_id['id'] for t_id in translations]

            vals = {
                'gengo_comment': term['gengo_comment'],
                'gengo_translation': term['gengo_translation'],
                'state': 'to_translate',
            }
            if translation_ids:
                IrTranslation.browse(translation_ids).write(vals)
            else:
                vals.update({
                    'name': 'website',
                    'lang': lang,
                    'source': initial_content,
                })
                IrTranslation.create(vals)
        return True
