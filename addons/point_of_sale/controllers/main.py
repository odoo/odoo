# -*- coding: utf-8 -*-
import logging
import werkzeug.utils

from openerp import http
from openerp.http import request

_logger = logging.getLogger(__name__)


class PosController(http.Controller):

    @http.route('/pos/web', type='http', auth='user')
    def a(self, debug=False, **k):
        session = request.session

        # if user not logged in, log him in
        pos_session = request.env['pos.session'].search(
            [('state', '=', 'opened'), ('user_id', '=', session.uid)])
        if not pos_session:
            return werkzeug.utils.redirect('/web#action=point_of_sale.action_pos_session_opening')
        pos_session.login()

        return request.render('point_of_sale.index')
