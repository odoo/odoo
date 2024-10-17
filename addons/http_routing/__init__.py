# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

from odoo.http import request

from .models.ir_http import IrHttp
from .models.ir_qweb import IrQweb
from .models.res_lang import ResLang


def _post_init_hook(env):
    if request:
        request.is_frontend = False
        request.is_frontend_multilang = False
