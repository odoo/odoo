# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from odoo.http import Controller, Response, request, route


class WebsiteGengo(Controller):
    @route('/website/gengo_callback', type='http', auth='none', csrf=False)
    def gengo_callback(self, **post):
        IrTranslationSudo = request.env['ir.translation'].sudo()
        if post.get('job') and post.get('pgk'):
            if post.get('pgk') != request.env['base.gengo.translations'].sudo().get_gengo_key():
                return Response("Bad authentication", status=104)
            job = json.loads(post['job'], 'utf-8')
            tid = job.get('custom_data')
            if job.get('status') == 'approved' and tid:
                term = IrTranslationSudo.browse(int(tid))
                if term.src != job.get('body_src'):
                    return Response("Text Altered - Not saved", status=418)

                translations = IrTranslationSudo.search([
                    '|',
                    ('id', "=", int(tid)),
                    '&', '&', '&', '&', '&',
                    ('state', '=', term.state),
                    ('gengo_translation', '=', term.gengo_translation),
                    ('src', "=", term.src),
                    ('type', "=", term.type),
                    ('name', "=", term.name),
                    ('lang', "=", term.lang),
                ])

                if translations:
                    translations.write({'state': 'translated',
                                        'value': job.get('body_tgt').replace('<', "&lt;").replace('>', "&gt;")})
                    return Response("OK", status=200)
                else:
                    return Response("No terms found", status=412)
        return Response("Not saved", status=418)
