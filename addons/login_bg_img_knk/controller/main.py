# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

import base64
from odoo.http import Controller, request, route
from werkzeug.utils import redirect

DEFAULT_IMAGE = 'login_bg_img_knk/static/src/img/bg.jpg'


class DasboardBackground(Controller):

    @route(['/dashboard'], type='http', auth="public")
    def dashboard(self, **post):
        user = request.env.user
        company = user.company_id
        if company.bg_image:
            image = base64.b64decode(company.bg_image)
        else:
            return redirect(DEFAULT_IMAGE)

        return request.make_response(
            image, [('Content-Type', 'image')])
