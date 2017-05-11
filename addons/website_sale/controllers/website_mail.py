# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from werkzeug import urls

from odoo import http
from odoo.http import request

from odoo.addons.website_mail.controllers.main import WebsiteMail


class WebsiteMailController(WebsiteMail):

    @http.route(['/website_mail/post/json'], type='json', auth='public', website=True)
    def chatter_json(self, res_model='', res_id=None, message='', **kw):
        params = kw.copy()
        params.pop('rating', False)
        message_data = super(WebsiteMailController, self).chatter_json(res_model=res_model, res_id=res_id, message=message, **params)
        if message_data and kw.get('rating') and res_model == 'product.template':  # restrict rating only for product template
            res_model_id = request.env.ref('product.model_product_template').id
            rating = request.env['rating.rating'].create({
                'rating': float(kw.get('rating')),
                'res_model_id': res_model_id,
                'res_id': res_id,
                'message_id': message_data['id'],
                'consumed': True,
            })
            message_data.update({
                'rating_default_value': rating.rating,
                'rating_disabled': True,
            })
        return message_data

    @http.route(['/website_mail/post/post'], type='http', methods=['POST'], auth='public', website=True)
    def chatter_post(self, res_model='', res_id=None, message='', redirect=None, **kw):
        params = kw.copy()
        params.pop('rating')
        response = super(WebsiteMailController, self).chatter_post(res_model=res_model, res_id=res_id, message=message, redirect=redirect, **params)
        if kw.get('rating') and res_model == 'product.template':  # restrict rating only for product template
            try:
                fragment = urls.url_parse(response.location).fragment
                message_id = int(fragment.replace('message-', ''))
                res_model_id = request.env.ref('product.model_product_template').id
                request.env['rating.rating'].create({
                    'rating': float(kw.get('rating')),
                    'res_model_id': res_model_id,
                    'res_id': res_id,
                    'message_id': message_id,
                    'consumed': True,
                })
            except Exception:
                pass
        return response
