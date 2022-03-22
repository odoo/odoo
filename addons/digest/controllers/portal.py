# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.urls import url_encode

from odoo import _
from odoo.http import Controller, request, Response, route
from odoo.tools import consteq


class DigestController(Controller):

    # csrf is disabled here because it will be called by the MUA with unpredictable session at that time
    @route('/digest/<int:digest_id>/unsubscribe_oneclik', type='http', website=True, auth='public',
           methods=['POST'], csrf=False)
    def digest_unsubscribe_oneclick(self, digest_id, token=None, user_id=None):
        """ Propose a one click button to the user to unsubscribe as defined in
        Only POST method is allowed preventing the risk that anti-spam trigger unwanted
        unsubscribe (scenario explained in the same rfc). Note: this method
        must support encoding method 'multipart/form-data' and 'application/x-www-form-urlencoded'.
        """
        self.digest_unsubscribe(digest_id, token=token, user_id=user_id)
        return Response(status=200)

    @route('/digest/<int:digest_id>/unsubscribe', type='http', website=True, auth='public')
    def digest_unsubscribe(self, digest_id, token=None, user_id=None):
        """ Unsubscribe a given user from a given digest

        :param int digest_id: id of digest to unsubscribe from
        :param str token: token preventing URL forgery
        :param user_id: id of user to unsubscribe
        """
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
