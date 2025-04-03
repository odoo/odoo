# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


class RedsysController(http.Controller):
    _return_url = '/payment/redsys/return'

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def redsys_return_from_checkout(self, **data):
        pass
