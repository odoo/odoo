# -*- coding: utf-8 -*-

import werkzeug
from openerp import http
from openerp.http import request


class Rating(http.Controller):

    @http.route('/rating/<string:token>/<int:rate>', type='http', auth="public")
    def add_rating(self, token, rate, **kwargs):
        Rating = request.env['rating.rating']
        rating = Rating.search([('access_token', '=', token)])
        if rating:
            is_rated = bool(rating.rating != -1)
            if not is_rated:
                record_sudo = request.env[rating.res_model].sudo().browse(rating.res_id)
                record_sudo.rating_apply(rate, token=token)
                # redirect to the form view if logged person
                if request.session.uid:
                    return werkzeug.utils.redirect('/web#model=%s&id=%s&view_type=form' % (record_sudo._name, record_sudo.id))
            return request.render('rating.rating_external_page_view', {'rating': rate, 'is_rated': is_rated})
        return request.not_found()
