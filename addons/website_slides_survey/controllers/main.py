# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.addons.website_slides.controllers.main import WebsiteSlides


class WebsiteSlidesSurvey(WebsiteSlides):
    # Profile
    # ---------------------------------------------------
    def _prepare_open_slide_user(self, user):
        values = super(WebsiteSlidesSurvey, self)._prepare_open_slide_user(user)

        survey_done = request.env['survey.user_input'].sudo().search(['&', ('partner_id', '=', user.partner_id.id), ('state', '=', 'done')])
        certificates = survey_done.filtered(lambda s: s.survey_id.certificate)

        values.update({
            'certificates': certificates,
        })
        return values
