# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.http import Controller, Response, request, route


class website_gengo(Controller):

    @route('/website/gengo_callback', type='http', auth='public', csrf=False)
    def gengo_callback(self, **post):
        IrTranslationSudo = request.env['ir.translation'].sudo()
        if post and post.get('job') and post.get('pgk'):
            if post.get('pgk') != request.env['base.gengo.translation'].sudo()._get_gengo_key():
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

                all_ir_tanslations = IrTranslationSudo.search(domain)

                if all_ir_tanslations:
                    all_ir_tanslations.write({
                        'state': 'translated',
                        'value': job.get('body_tgt')
                    })
                    return Response("OK", status=200)
                else:
                    return Response("No terms found", status=412)
        return Response("Not saved", status=418)
