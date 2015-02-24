# -*- coding: utf-8 -*-

import json
from werkzeug.wrappers import BaseResponse as Response

from openerp import http
from openerp.http import request


class WebsiteGengo(http.Controller):

    def get_gengo_key(self):
        IrConfigParamSudo = request.env['ir.config_parameter'].sudo()
        return IrConfigParamSudo.get_param(request.env['base.gengo.translations'].GENGO_KEY, default="")

    @http.route('/website/gengo_callback', type='http', auth='none')
    def gengo_callback(self, **post):
        IrTranslationSudo = request.env['ir.translation'].sudo()
        if post.get('job') and post.get('pgk'):
            if post.get('pgk') != self.get_gengo_key():
                return Response("Bad authentication", status=104)
            job = json.loads(post['job'], 'utf-8')
            tid = job.get('custom_data', False)
            if (job.get('status') == 'approved') and tid:
                term = IrTranslationSudo.browse(int(tid))
                if term.src != job.get('body_src'):
                    return Response("Text Altered - Not saved", status=418)
                domain = [
                    '|',
                    ('id', "=", int(tid)),
                    '&', '&', '&', '&', '&',
                    ('state', '=', term.state),
                    ('gengo_translation', '=', term.gengo_translation),
                    ('src', "=", term.src),
                    ('type', "=", term.type),
                    ('name', "=", term.name),
                    ('lang', "=", term.lang),
                    #('order_id', "=", term.order_id),
                ]

                all_ir_translations = IrTranslationSudo.search(domain)

                if all_ir_translations:
                    vals = {'state': 'translated', 'value': job.get('body_tgt')}
                    all_ir_translations.write(vals)
                    return Response("OK", status=200)
                else:
                    return Response("No terms found", status=412)
        return Response("Not saved", status=418)
