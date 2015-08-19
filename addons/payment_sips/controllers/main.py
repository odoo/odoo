# -*- coding: utf-8 -*-

try:
    import simplejson as json
except ImportError:
    import json
import logging
import werkzeug

from openerp import http
from openerp.http import request

_logger = logging.getLogger(__name__)


class SipsController(http.Controller):
    _notify_url = '/payment/sips/ipn/'
    _return_url = '/payment/sips/dpn/'

    def _get_return_url(self, **post):
        """ Extract the return URL from the data coming from sips. """
        return_url = post.pop('return_url', '')
        if not return_url:
            tx_obj = request.registry['payment.transaction']
            data = tx_obj._sips_data_to_object(post.get('Data'))
            custom = json.loads(data.pop('returnContext', False) or '{}')
            return_url = custom.get('return_url', '/')
        return return_url

    def sips_validate_data(self, **post):
        res = False
        env = request.env
        tx_obj = env['payment.transaction']
        acquirer_obj = env['payment.acquirer']

        sips = acquirer_obj.search([('provider', '=', 'sips')], limit=1)

        security = sips._sips_generate_shasign(post)
        if security == post['Seal']:
            _logger.debug('Sips: validated data')
            res = tx_obj.sudo().form_feedback(post, 'sips')
        else:
            _logger.warning('Sips: data are corrupted')
        return res

    @http.route([
        '/payment/sips/ipn/'],
        type='http', auth='none', methods=['POST'])
    def sips_ipn(self, **post):
        """ Sips IPN. """
        self.sips_validate_data(**post)
        return ''

    @http.route([
        '/payment/sips/dpn'], type='http', auth="none", methods=['POST'])
    def sips_dpn(self, **post):
        """ Sips DPN """
        return_url = self._get_return_url(**post)
        self.sips_validate_data(**post)
        return werkzeug.utils.redirect(return_url)
