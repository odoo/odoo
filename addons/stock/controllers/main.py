# -*- coding: utf-8 -*-
import logging

from openerp import http
from openerp.http import request

_logger = logging.getLogger(__name__)

class BarcodeController(http.Controller):

    @http.route(['/stock/barcode/'], type='http', auth='user')
    def a(self, debug=False, **k):
        if not request.session.uid:
            return http.local_redirect('/web/login?redirect=/stock/barcode/')

        return request.render('stock.barcode_index')
