# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Original Copyright 2015 Eezee-It, modified and maintained by Odoo.

import logging
import pprint

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class SipsController(http.Controller):
    _return_url = '/payment/sips/dpn/'
    _notify_url = '/payment/sips/ipn/'

    @http.route(
        _return_url, type='http', auth='public', methods=['POST'], csrf=False, save_session=False
    )
    def sips_dpn(self, **post):
        """ Process the data returned by SIPS after redirection.

        The route is flagged with `save_session=False` to prevent Odoo from assigning a new session
        to the user if they are redirected to this route with a POST request. Indeed, as the session
        cookie is created without a `SameSite` attribute, some browsers that don't implement the
        recommended default `SameSite=Lax` behavior will not include the cookie in the redirection
        request from the payment provider to Odoo. As the redirection to the '/payment/status' page
        will satisfy any specification of the `SameSite` attribute, the session of the user will be
        retrieved and with it the transaction which will be immediately post-processed.

        :param dict post: The feedback data to process
        """
        _logger.info("beginning Sips DPN _handle_feedback_data with data %s", pprint.pformat(post))
        try:
            if self._sips_validate_data(post):
                request.env['payment.transaction'].sudo()._handle_feedback_data('sips', post)
        except ValidationError:
            pass
        return request.redirect('/payment/status')

    @http.route(_notify_url, type='http', auth='public', methods=['POST'], csrf=False)
    def sips_ipn(self, **post):
        """ Sips IPN. """
        _logger.info("beginning Sips IPN _handle_feedback_data with data %s", pprint.pformat(post))
        if not post:
            # SIPS sometimes sends empty notifications, the reason why is unclear but they tend to
            # pollute logs and do not provide any meaningful information; log as a warning instead
            # of a traceback.
            _logger.warning("received empty notification; skip.")
        else:
            try:
                if self._sips_validate_data(post):
                    request.env['payment.transaction'].sudo()._handle_feedback_data('sips', post)
            except ValidationError:
                pass  # Acknowledge the notification to avoid getting spammed
        return ''

    def _sips_validate_data(self, post):
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_feedback_data('sips', post)
        acquirer_sudo = tx_sudo.acquirer_id
        security = acquirer_sudo._sips_generate_shasign(post['Data'])
        if security == post['Seal']:
            _logger.debug('validated data')
            return True
        else:
            _logger.warning('data are tampered')
            return False
