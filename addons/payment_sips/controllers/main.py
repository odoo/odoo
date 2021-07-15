# -*- coding: utf-8 -*-

# Copyright 2015 Eezee-It

import json
import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SipsController(http.Controller):
    _notify_url = '/payment/sips/ipn/'
    _return_url = '/payment/sips/dpn/'

    def sips_validate_data(self, **post):
        sips = request.env['payment.acquirer'].search([('provider', '=', 'sips')], limit=1)
        security = sips.sudo()._sips_generate_shasign(post)
        if security == post['Seal']:
            _logger.debug('Sips: validated data')
            return request.env['payment.transaction'].sudo().form_feedback(post, 'sips')
        _logger.warning('Sips: data are corrupted')
        return False

    @http.route('/payment/sips/ipn/', type='http', auth='public', methods=['POST'], csrf=False)
    def sips_ipn(self, **post):
        """ Sips IPN. """
        _logger.info('Beginning Sips IPN form_feedback with post data %s', pprint.pformat(post))  # debug
        if not post:
            # SIPS sometimes sends empty notifications, the reason why is
            # unclear but they tend to pollute logs and do not provide any
            # meaningful information; log as a warning instead of a traceback
            _logger.warning('Sips: received empty notification; skip.')
        else:
            self.sips_validate_data(**post)
        return ''

    @http.route('/payment/sips/dpn', type='http', auth="public", methods=['POST'], csrf=False, save_session=False)
    def sips_dpn(self, **post):
        """ Sips DPN
        The session cookie created by Odoo has not the attribute SameSite. Most of browsers will force this attribute
        with the value 'Lax'. After the payment, Sips will perform a POST request on this route. For all these reasons,
        the cookie won't be added to the request. As a result, if we want to save the session, the server will create
        a new session cookie. Therefore, the previous session and all related information will be lost, so it will lead
        to undesirable behaviors. This is the reason why `save_session=False` is needed.
        """
        try:
            _logger.info('Beginning Sips DPN form_feedback with post data %s', pprint.pformat(post))  # debug
            self.sips_validate_data(**post)
        except:
            pass
        return werkzeug.utils.redirect('/payment/process')
