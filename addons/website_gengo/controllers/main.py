# -*- coding: utf-8 -*-

import openerp
from openerp import http, SUPERUSER_ID
from openerp.http import request
import time

GENGO_DEFAULT_LIMIT = 20

class website_gengo(http.Controller):

    @http.route('/website/get_translated_length', type='json', auth='user', website=True)
    def get_translated_length(self, translated_ids, lang):
        ir_translation_obj = request.registry['ir.translation']
        result={"done":0}
        gengo_translation_ids = ir_translation_obj.search(request.cr, request.uid, [('id','in',translated_ids),('gengo_translation','!=', False)])
        for trans in ir_translation_obj.browse(request.cr, request.uid, gengo_translation_ids):
            result['done'] += len(trans.source.split())
        return result
    
    @http.route('/website/check_gengo_set', type='json', auth='user', website=True)
    def check_gengo_set(self):
        user = request.registry['res.users'].browse(request.cr, SUPERUSER_ID, request.uid)
        company_flag = 0
        if not user.company_id.gengo_public_key or not user.company_id.gengo_private_key:
            company_flag = user.company_id.id
        return company_flag
    
    @http.route('/website/set_gengo_config', type='json', auth='user', website=True)
    def set_gengo_config(self,config):
        user = request.registry['res.users'].browse(request.cr, request.uid, request.uid)
        if user.company_id:
            request.registry['res.company'].write(request.cr, request.uid, user.company_id.id, config)
        return True

    @http.route('/website/post_gengo_jobs', type='json', auth='user', website=True)
    def post_gengo_jobs(self):
        request.registry['base.gengo.translations']._sync_request(request.cr, request.uid, limit=GENGO_DEFAULT_LIMIT, context=request.context)
        return True
