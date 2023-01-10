# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.urls import url_encode

from odoo import _
from odoo.http import Controller, request, route
from odoo.tools import consteq


class DigestController(Controller):

    @route('/digest/<int:digest_id>/unsubscribe', type='http', website=True, auth='public')
    def digest_unsubscribe(self, digest_id, token=None, user_id=None):
        digest_sudo = request.env['digest.digest'].sudo().browse(digest_id).exists()

        # new route parameters
        if digest_sudo and token and user_id:
            correct_token = digest_sudo._get_unsubscribe_token(int(user_id))
            if not consteq(correct_token, token):
                raise NotFound()
            digest_sudo._action_unsubscribe_users(request.env['res.users'].sudo().browse(int(user_id)))
        # old route was given without any token or user_id but only for auth users
        elif digest_sudo and not token and not user_id and not request.env.user.share:
            digest_sudo.action_unsubcribe()
        else:
            raise NotFound()

        return request.render('digest.portal_digest_unsubscribed', {
            'digest': digest_sudo,
        })

    @route('/digest/<int:digest_id>/set_periodicity', type='http', website=True, auth='user')
    def digest_set_periodicity(self, digest_id, periodicity='weekly'):
        if not request.env.user.has_group('base.group_erp_manager'):
            raise Forbidden()
        if periodicity not in ('daily', 'weekly', 'monthly', 'quarterly'):
            raise ValueError(_('Invalid periodicity set on digest'))

        digest = request.env['digest.digest'].browse(digest_id).exists()
        digest.action_set_periodicity(periodicity)

        url_params = {
            'model': digest._name,
            'id': digest.id,
            'active_id': digest.id,
        }
        return request.redirect('/web?#%s' % url_encode(url_params))
