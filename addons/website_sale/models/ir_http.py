# -*- coding: utf-8 -*-
from openerp import models
from openerp.addons.web.http import request

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def _dispatch(self):
        affiliate_id = request.httprequest.args.get('affiliate_id')
        if affiliate_id:
            request.session['affiliate_id'] = int(affiliate_id)
        return super(IrHttp, self)._dispatch()
