# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, fields, models
from odoo.exceptions import UserError

from .authorize_request import AuthorizeAPI
from odoo.addons import payment

_logger = logging.getLogger(__name__)


class PaymentToken(payment.PaymentToken):

    authorize_profile = fields.Char(
        string="Authorize.Net Profile ID",
        help="The unique reference for the partner/token combination in the Authorize.net backend.")
