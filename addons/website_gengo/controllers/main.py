# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request
class website_gengo(http.Controller):

    @http.route('/website/get_gengo_info', type='json', auth='user', website=True)
    def get_gengo_info(self, view_id, lang):
        ir_translation_obj = request.registry['ir.translation']
        res_lang_obj = request.registry['res.lang']
        translation_ids = ir_translation_obj.search(request.cr, request.uid, [('res_id','=',view_id),('gengo_translation','!=', False),('lang','=',lang)])
        result={"total":0,"inprogess":0,"done":0}
        for trans in ir_translation_obj.browse(request.cr, request.uid, translation_ids):
            result['total'] += len(trans.source.split())
            if trans.state == 'translated':
                result['done'] += len(trans.source.split())
            elif trans.state in ['inprogress','to_translate']:
                result['inprogess'] += len(trans.source.split())
        return result
