# -*- coding: utf-8 -*-

import werkzeug
from openerp import http
from openerp.http import request


class Rating(http.Controller):

    @http.route('/rating/<string:token>/<int:rate>', type='http', auth="public")
    def add_rating(self, token, rate, **kwargs):
        rating = request.env['rating.rating'].search([('access_token', '=', token)])
        if rating:
            is_rated = bool(rating.rating != -1)
            if not is_rated:
                rating.sudo().apply_rating(rate, token=token)
            return request.render('rating.rating_external_page_view', {'rating': rate, 'is_rated': is_rated, 'token': token})
        return request.not_found()

    @http.route(['/rating/<string:token>/feedback', '/rating/<string:token>/cancel'], type="http", auth="public", method=['post'])
    def add_feedback(self, token, **kwargs):
        rating = request.env['rating.rating'].search([('access_token', '=', token)])
        if rating:
            if kwargs.get('feedback'):
                rating.sudo().write({'feedback': kwargs.get('feedback')})
            # redirect to the form view if logged person
            if request.session.uid:
                record = request.env[rating.res_model].browse(rating.res_id)
                return werkzeug.utils.redirect('/web#model=%s&id=%s&view_type=form' % (record._name, record.id))
            return request.render('rating.rating_external_page_view', {'is_public': True})
        return request.not_found()
