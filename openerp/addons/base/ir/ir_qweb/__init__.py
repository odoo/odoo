# -*- coding: utf-8 -*-
from openerp.tools import safe_eval, html_escape as escape

from . import fields
from . import assetsbundle
from . import utils

from .assetsbundle import AssetsBundle
from .utils import QWebContext, unicodifier
from .qweb import QWeb
