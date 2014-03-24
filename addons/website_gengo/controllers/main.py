# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request
class website_gengo(http.Controller):

    @http.route('/website/get_translated_length', type='json', auth='user', website=True)
    def get_translated_length(self, translated_ids, lang):
        ir_translation_obj = request.registry['ir.translation']
        result={"done":0}
        gengo_translation_ids = ir_translation_obj.search(request.cr, request.uid, [('id','in',translated_ids),('gengo_translation','!=', False)])
        for trans in ir_translation_obj.browse(request.cr, request.uid, gengo_translation_ids):
            result['done'] += len(trans.source.split())
        return result
