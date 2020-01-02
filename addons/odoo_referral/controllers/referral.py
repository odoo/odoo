# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, request, route


class Referral(Controller):

    @route(['/referral/go'], type='json', auth='user', method='POST', website=True)
    def referral_go(self, **kwargs):
        request.env.user.referral_updates_count = 0
        return {'link': request.env.user._get_referral_link()}
