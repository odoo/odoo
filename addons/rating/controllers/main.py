# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import http
from odoo.http import request
from odoo.tools.translate import _
from odoo.tools.misc import get_lang

_logger = logging.getLogger(__name__)

MAPPED_RATES = {
    1: 1,
    5: 3,
    10: 5,
}

class Rating(http.Controller):

    @http.route('/rating/<string:token>/<int:rate>', type='http', auth="public", website=True)
    def open_rating(self, token, rate, **kwargs):
        _logger.warning('/rating is deprecated, use /rate instead')
        assert rate in (1, 5, 10), "Incorrect rating"
        return self.action_open_rating(token, MAPPED_RATES.get(rate), **kwargs)

    @http.route(['/rating/<string:token>/submit_feedback'], type="http", auth="public", methods=['post'], website=True)
    def submit_rating(self, token, **kwargs):
        _logger.warning('/rating is deprecated, use /rate instead')
        rate = int(kwargs.get('rate'))
        assert rate in (1, 5, 10), "Incorrect rating"
        kwargs['rate'] = MAPPED_RATES.gate(rate)
        return self.action_submit_rating(token, **kwargs)

    @http.route('/rate/<string:token>/<int:rate>', type='http', auth="public", website=True)
    def action_open_rating(self, token, rate, **kwargs):
        assert rate in (1, 3, 5), "Incorrect rating"
        rating = request.env['rating.rating'].sudo().search([('access_token', '=', token)])
        if not rating:
            return request.not_found()
        rate_names = {
            5: _("Satisfied"),
            3: _("Okay"),
            1: _("Dissatisfied")
        }
        rating.write({'rating': rate, 'consumed': True})
        lang = rating.partner_id.lang or get_lang(request.env).code
        return request.env['ir.ui.view'].with_context(lang=lang)._render_template('rating.rating_external_page_submit', {
            'rating': rating, 'token': token,
            'rate_names': rate_names, 'rate': rate
        })

    @http.route(['/rate/<string:token>/submit_feedback'], type="http", auth="public", methods=['post', 'get'], website=True)
    def action_submit_rating(self, token, **kwargs):
        rating = request.env['rating.rating'].sudo().search([('access_token', '=', token)])
        if not rating:
            return request.not_found()
        if request.httprequest.method == "POST":
            rate = int(kwargs.get('rate'))
            assert rate in (1, 3, 5), "Incorrect rating"
            record_sudo = request.env[rating.res_model].sudo().browse(rating.res_id)
            record_sudo.rating_apply(rate, token=token, feedback=kwargs.get('feedback'))
        lang = rating.partner_id.lang or get_lang(request.env).code
        return request.env['ir.ui.view'].with_context(lang=lang)._render_template('rating.rating_external_page_view', {
            'web_base_url': rating.get_base_url(),
            'rating': rating,
        })
