# -*- coding: utf-8 -*-

import logging
import random

from odoo import http
from odoo.http import request

logger = logging.getLogger(__name__)

class RagBot(http.Controller):
    @http.route('/ragbot/chat', type='json', auth='user')
    def get_response(self):
        """

        """
        return {
            "The chatbot's response"
        }

