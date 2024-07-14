# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tools import config
from . import models


def pre_init_hook(cr):
    if not config.get("init") and not config.get("update"):
        raise UserError("The Taxcloud module is deprecated and cannot be installed. Consider installing the Avatax module instead.")
