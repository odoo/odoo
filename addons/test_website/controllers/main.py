# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.web import Home


class WebsiteTest(Home):

    @http.route('/test_view', type='http', auth="public", website=True)
    def test_view(self, **kw):
        return request.render('test_website.test_view')
