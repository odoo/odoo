# -*- coding: utf-8 -*-
import traceback
import werkzeug
import openerp
from openerp.http import request
from openerp.osv import orm

class ir_http(orm.AbstractModel):
    _inherit = 'ir.http'

    def _handle_exception(self, exception=None, code=500):
        #At this time it gives error when user's email address is not configured instead of raise exception so redirect user to update profile.
        #when website will handle exception then remove this code.
        if exception and exception[1] and exception[1] == "Unable to send email, please configure the sender's email address or alias.":
            forum = request.httprequest.path.strip('/forum').split('/')
            return werkzeug.utils.redirect("/forum/%s/edit/profile/%s" % (forum[0],request.uid))
        return super(ir_http, self)._handle_exception(exception)
