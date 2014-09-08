# -*- coding: utf-8 -*-
import logging

from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import login_redirect

_logger = logging.getLogger(__name__)


class PosController(http.Controller):

    @http.route('/pos/web', type='http', auth='none')
    def a(self, debug=False, **k):

        if not request.session.uid:
            return login_redirect()

        return request.render('point_of_sale.index')
