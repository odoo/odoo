# -*- coding: utf-8 -*-
# Copyright (c) 2020-Present InTechual Solutions. (<https://intechualsolutions.com/>)

from odoo import http


class ChatgptController(http.Controller):
    @http.route(['/chatgpt_form'], type='http', auth="public", csrf=False,
                website=True)
    def question_submit(self):
        return http.request.render('is_chatgpt_integration.connector')
