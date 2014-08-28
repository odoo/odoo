# -*- coding: utf-8 -*-
from openerp.http import request
from openerp.osv import orm


class ir_http(orm.AbstractModel):
    _inherit = 'ir.http'

    def _dispatch(self):
        for var, dummy in self.pool['crm.tracking.mixin'].tracking_fields():
            if var in request.params and (var not in request.session or request.session[var] != request.params[var]):
                    request.session[var] = request.params[var]
        return super(ir_http, self)._dispatch()
