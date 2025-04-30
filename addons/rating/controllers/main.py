# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import werkzeug

from odoo import http
from odoo.http import request
from odoo.tools.translate import _
from odoo.tools.misc import get_lang
from odoo.addons.rating.models.rating_data import (
    RATING_HAPPY_VALUE,
    RATING_NEUTRAL_VALUE,
    RATING_UNHAPPY_VALUE,
)

_logger = logging.getLogger(__name__)

MAPPED_RATES = {
    1: RATING_UNHAPPY_VALUE,
    5: RATING_NEUTRAL_VALUE,
    10: RATING_HAPPY_VALUE,
}

class Rating(http.Controller):

    @http.route('/rate/<string:token>/<int:rate>', type='http', auth="public", website=True)
    def action_open_rating(self, token, rate, **kwargs):
        if rate not in (RATING_HAPPY_VALUE, RATING_NEUTRAL_VALUE, RATING_UNHAPPY_VALUE):
            raise ValueError(
                _("Incorrect rating: should be %(rating_unhappy)d, %(rating_neutral)d or %(rating_happy)d (received %(rate)d)"),
                rating_unhappy=RATING_UNHAPPY_VALUE,
                rating_neutral=RATING_NEUTRAL_VALUE,
                rating_happy=RATING_HAPPY_VALUE,
                rate=rate,
            )

        # This route used to allow sending a rating with a GET, the
        # feature proved incompatible with various email provider URL crawlers and
        # has been removed.
        rating, record_sudo = self._get_rating_and_record(token)

        if not request.env.user._is_public() and \
                request.env.user.partner_id.commercial_partner_id != rating.partner_id.commercial_partner_id:
            return request.render('rating.rating_external_page_invalid_partner', {
                'model_name': request.env['ir.model']._get(rating.res_model).display_name,
                'name': record_sudo.display_name,
                'web_base_url': rating.get_base_url(),
            })

        lang = rating.partner_id.lang or get_lang(request.env).code
        return request.env['ir.ui.view'].with_context(lang=lang)._render_template('rating.rating_external_page_submit', {
            'rating': rating,
            'token': token,
            'rate_names': {
                RATING_HAPPY_VALUE: _("Happy"),
                RATING_NEUTRAL_VALUE: _("Neutral"),
                RATING_UNHAPPY_VALUE: _("Unhappy"),
            },
            'rate': rate,
        })

    @http.route(['/rate/<string:token>/submit_feedback'], type="http", auth="public", methods=['post', 'get'], website=True)
    def action_submit_rating(self, token, rate=0, **kwargs):

        rating, record_sudo = self._get_rating_and_record(token)
        if request.httprequest.method == "POST":
            rate = int(rate)
            if rate not in (RATING_HAPPY_VALUE, RATING_NEUTRAL_VALUE, RATING_UNHAPPY_VALUE):
                raise ValueError(
                    _("Incorrect rating: should be %(rating_unhappy)d, %(rating_neutral)d or %(rating_happy)d (received %(rate)d)"),
                    rating_unhappy=RATING_UNHAPPY_VALUE,
                    rating_neutral=RATING_NEUTRAL_VALUE,
                    rating_happy=RATING_HAPPY_VALUE,
                    rate=rate,
                )
            record_sudo.rating_apply(
                rate,
                rating=rating,
                feedback=kwargs.get('feedback'),
                subtype_xmlid=None,  # force default subtype choice
            )

        lang = rating.partner_id.lang or get_lang(request.env).code
        return request.env['ir.ui.view'].with_context(lang=lang)._render_template('rating.rating_external_page_view', {
            'web_base_url': rating.get_base_url(),
            'rating': rating,
        })

    def _get_rating_and_record(self, token):
        rating_sudo = request.env['rating.rating'].sudo().search([('access_token', '=', token)])
        if not rating_sudo:
            raise werkzeug.exceptions.NotFound()

        record_sudo = request.env[rating_sudo.res_model].sudo().browse(rating_sudo.res_id)
        if not record_sudo.exists():
            raise werkzeug.exceptions.NotFound()
        return rating_sudo, record_sudo
