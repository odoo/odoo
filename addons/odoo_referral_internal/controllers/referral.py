# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.http import Controller, route, request


class Referral(Controller):

    @route('/referral/notifications/<string:token>', type='json', auth='public', website=True)
    def referral_notifications(self, token, **kwargs):
        referral_tracking = request.env['referral.tracking'].sudo().search([('token', '=', token)], limit=1)
        if not referral_tracking:
            return {}
        num_notif = referral_tracking.updates_count
        referral_tracking.updates_count = 0
        return {'updates_count': num_notif}
