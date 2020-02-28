# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _dispatch_call(cls):
        # add signup token or login to the session if given

        print ('auth signup',request)
        print ('auth signup',request.params)
        if 'auth_signup_token' in request.params:
            request.session['auth_signup_token'] = request.params['auth_signup_token']
        if 'auth_login' in request.params:
            request.session['auth_login'] = request.params['auth_login']

        return super(Http, cls)._dispatch_call()
