# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, fields, models
from odoo.exceptions import UserError

from .authorize_request import AuthorizeAPI

_logger = logging.getLogger(__name__)


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    authorize_profile = fields.Char(
        string="Authorize.Net Profile ID",
        help="The unique reference for the partner/token combination in the Authorize.net backend.")

    def _handle_deactivation_request(self):
        """ Override of payment to request Authorize.Net to delete the token.

        Note: self.ensure_one()

        :return: None
        """
        super()._handle_deactivation_request()
        if self.provider != 'authorize':
            return

        authorize_API = AuthorizeAPI(self.acquirer_id)
        res_content = authorize_API.delete_customer_profile(self.authorize_profile)
        _logger.info("delete_customer_profile request response:\n%s", pprint.pformat(res_content))

    def _handle_reactivation_request(self):
        """ Override of payment to raise an error informing that Auth.net tokens cannot be restored.

        Note: self.ensure_one()

        :return: None
        """
        super()._handle_reactivation_request()
        if self.provider != 'authorize':
            return

        raise UserError(_("Saved payment methods cannot be restored once they have been deleted."))
