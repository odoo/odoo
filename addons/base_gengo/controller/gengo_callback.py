# -*- coding: utf-8 -*-

import openerp
from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request

from werkzeug.wrappers import BaseResponse as Response

import json


class website_gengo(http.Controller):

    def get_gengo_key(self, cr):
        icp = request.registry['ir.config_parameter']
        return icp.get_param(cr, SUPERUSER_ID, request.registry['base.gengo.translations'].GENGO_KEY, default="")

    @http.route('/website/gengo_callback', type='http', auth='none', csrf=False)
    def gengo_callback(self, **post):
        print "IN website/gengo_callback"
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        translation_pool = request.registry['ir.translation']
        if post and post.get('job') and post.get('pgk'):
            if post.get('pgk') != self.get_gengo_key(cr):
                return Response("Bad authentication", status=104)
            job = json.loads(post['job'], 'utf-8')
            tid = job.get('custom_data', False)
            if (job.get('status') == 'approved') and tid:
                term = translation_pool.browse(cr, uid, int(tid), context=context)
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

                all_ir_tanslations = translation_pool.search(cr, uid, domain, context=context or {})

                if all_ir_tanslations:
                    vals = {'state': 'translated', 'value': job.get('body_tgt')}
                    translation_pool.write(cr, uid, all_ir_tanslations, vals, context=context)
                    return Response("OK", status=200)
                else:
                    return Response("No terms found", status=412)
        return Response("Not saved", status=418)
