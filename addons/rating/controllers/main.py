# -*- coding: utf-8 -*-

import werkzeug
from openerp import http
from openerp.http import request


class Rating(http.Controller):

    @http.route('/rating/<string:token>/<int:rate>', type='http', auth="public")
    def open_rating(self, token, rate, **kwargs):
        token_rec = request.env['rating.token'].sudo().search([('access_token', '=', token)])
        if token_rec:
            if not token_rec.rating_id.rating:
                return request.render('rating.rating_form', {'rating': rate, 'token': token})
            else:
                return request.render('rating.rating_result', {'is_rated': True})
        return request.not_found()

    @http.route(['/rating/<string:token>/<int:rate>/submit_feedback'], type="http", auth="public", method=['post'])
    def submit_rating(self, token, rate, **kwargs):
        token_rec = request.env['rating.token'].sudo().search([('access_token', '=', token)])
        if token_rec:
            if not token_rec.rating_id.rating:
                record_sudo = request.env[token_rec.res_model].sudo().browse(token_rec.res_id)
                record_sudo.rating_apply(rate, token=token, feedback=kwargs.get('feedback'))
                # redirect to the form view if logged person
                if request.session.uid:
                    return werkzeug.utils.redirect('/web#model=%s&id=%s&view_type=form' % (record_sudo._name, record_sudo.id))
                return request.render('rating.rating_result', {'is_public': True})
            else:
                return request.render('rating.rating_result', {'is_rated': True})
        return request.not_found()
