# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from threading import Thread

from odoo import models, api
from odoo.http import request
from odoo.modules.registry import Registry


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _dispatch(cls):
        result = super(IrHttp, cls)._dispatch()
        if not request.session.get('reveal') and request.is_frontend and request.httprequest.method == 'GET' and request._request_type == 'http' and not request.session.uid:
            request.session['reveal'] = True  # Mark session for reveal
            args = (request.env.cr.dbname, request.env.uid, request.httprequest.path, request.httprequest.remote_addr)
            Thread(target=cls.handle_reveal_request, args=args).start()
        return result

    @classmethod
    def handle_reveal_request(cls, dbname, uid, path, ip):
        with api.Environment.manage():
            with Registry(dbname).cursor() as cr:
                env = api.Environment(cr, uid, {})
                env['crm.reveal.rule'].sudo().process_reveal_request(path, ip)
