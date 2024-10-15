# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import IrHttp, IrQweb, ResLang

from odoo.http import request


def _post_init_hook(env):
    if request:
        request.is_frontend = False
        request.is_frontend_multilang = False
