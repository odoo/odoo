# -*- coding: utf-8 -*-

from openerp.http import request
from openerp.osv import orm
import json

class ir_http(orm.AbstractModel):
    _inherit = 'ir.http'

    def _dispatch(self):
        x = super(ir_http, self)._dispatch()
        if request.context.get('website_version_experiment'):
            data=json.dumps(request.context['website_version_experiment'], ensure_ascii=False)
            x.set_cookie('website_version_experiment', data)
        return x

    def get_page_key(self):
        key = super(ir_http, self).get_page_key()
        seq_ver = [int(ver) for ver in request.context.get('website_version_experiment', {}).values()]
        key += (str(sorted(seq_ver)),)
        return key
