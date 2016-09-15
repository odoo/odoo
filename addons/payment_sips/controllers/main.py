# -*- coding: utf-8 -*-

import json
import logging
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SipsController(http.Controller):
    _notify_url = '/payment/sips/ipn/'
    _return_url = '/payment/sips/dpn/'

    def _get_return_url(self, **post):
        """ Extract the return URL from the data coming from sips. """
        return_url = post.pop('return_url', '')
        if not return_url:
            Tx = request.env['payment.transaction']
            data = Tx._sips_data_to_object(post.get('Data'))
            custom = json.loads(data.pop('returnContext', False) or '{}')
            return_url = custom.get('return_url', '/')
        return return_url

    def sips_validate_data(self, **post):
        sips = request.env['payment.acquirer'].search([('provider', '=', 'sips')], limit=1)
        security = sips.sudo()._sips_generate_shasign(post)
        if security == post['Seal']:
            _logger.debug('Sips: validated data')
            return request.env['payment.transaction'].sudo().form_feedback(post, 'sips')
        _logger.warning('Sips: data are corrupted')
        return False

    @http.route([
        '/payment/sips/ipn/'],
        type='http', auth='none', methods=['POST'], csrf=False)
    def sips_ipn(self, **post):
        """ Sips IPN. """
        self.sips_validate_data(**post)
        return ''

    @http.route([
        '/payment/sips/dpn'], type='http', auth="none", methods=['POST'], csrf=False)
    def sips_dpn(self, **post):
        """ Sips DPN """
        return_url = self._get_return_url(**post)
        self.sips_validate_data(**post)
        return werkzeug.utils.redirect(return_url)
