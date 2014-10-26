# -*- coding: utf-8 -*-

from openerp.http import request
from openerp.osv import orm
import json

class ir_http(orm.AbstractModel):
    _inherit = 'ir.http'

    def _dispatch(self):
        x = super(ir_http, self)._dispatch()
        if request.context.get('EXP'):
            data=json.dumps(request.context['EXP'], ensure_ascii=False)
            x.set_cookie('EXP', data)
        return x

