# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request

import json

class website_gengo(http.Controller):
    @http.route('/website/gengo_callback', type='http', auth='none')
    def gengo_callback(self,**post):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        translation_pool = request.registry['ir.translation']
        if post and post.get('job'):
            job = json.loads(post['job'])
            tid = job.get('custom_data', False)
            if (job.get('status') == 'approved') and tid:
                term = translation_pool.browse(cr, uid, int(tid), context=context)
                if term.job_id <> job.get('job_id'):
                    raise 'Error'
                vals = {'state': 'translated', 'value': job.get('body_tgt')}
                translation_pool.write(cr, uid, [int(tid)], vals, context=context)
