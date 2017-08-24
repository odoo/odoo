# -*- coding: utf-8 -*-
from odoo.tools import safe_eval, html_escape as escape

from . import fields
from . import assetsbundle

from .assetsbundle import AssetsBundle
from .qweb import QWebException
from .ir_qweb import IrQWeb, QWeb
