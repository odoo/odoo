# -*- coding: utf-8 -*-

import werkzeug
from openerp import http
from openerp.http import request


class Rating(http.Controller):

    @http.route('/rating/<token>', type='http', auth="public")
    def rating(self, token=None, rating=None, **post):
        rating_obj = request.env['rating.rating']
        is_rated = rating_obj.sudo().search(
            [('access_token', '=', token), ('rating', '!=', -1)])
        if token and rating:
            if not is_rated:
                record = rating_obj.apply_rating(rating, token=token)
            else:
                record = request.env[
                    is_rated.res_model].sudo().browse(is_rated.res_id)
            if record and not request.session.uid:
                return request.render('rating.rating_view', {'value': record, 'rating': rating, 'is_rated': is_rated})
            elif record:
                return werkzeug.utils.redirect('/web#model=%s&id=%s&view_type=form' % (record._name, record.id))
        return request.render("rating.403")
