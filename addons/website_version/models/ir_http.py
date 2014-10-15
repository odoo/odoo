# -*- coding: utf-8 -*-
import datetime
import hashlib
import logging
import os
import re
import traceback

import werkzeug
import werkzeug.routing
import werkzeug.utils

import openerp
from openerp.addons.base import ir
from openerp.addons.base.ir import ir_qweb
from openerp.addons.website.models.website import slug, url_for, _UNSLUG_RE
from openerp.http import request
from openerp.tools import config
from openerp.osv import orm
import werkzeug.wrappers
import json

logger = logging.getLogger(__name__)

class ir_http(orm.AbstractModel):
    _inherit = 'ir.http'

    def _dispatch(self):
        x = super(ir_http, self)._dispatch()
        if request.context.get('EXP'):
            data=json.dumps(request.context['EXP'], ensure_ascii=False)
            x.set_cookie('EXP', data)
        return x

