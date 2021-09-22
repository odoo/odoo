# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden
from werkzeug.urls import url_encode

from odoo import _
from odoo.http import Controller, request, route


class DigestController(Controller):

    @route('/digest/<int:digest_id>/unsubscribe', type='http', website=True, auth='user')
    def digest_unsubscribe(self, digest_id):
        digest = request.env['digest.digest'].browse(digest_id).exists()
        digest.action_unsubcribe()
        return request.render('digest.portal_digest_unsubscribed', {
            'digest': digest,
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
