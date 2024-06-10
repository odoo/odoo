# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from .models import (
    Company,
    IrModelData,
    IrSequence,
    IrActions,
    IrActionsReport,
    IrConfigParameter,
    Country,
    Lang,
    Partner,
    ResConfigSettings,
    Currency,
    Company,
    Users,
    DecimalPrecision,
)
from . import populate
from . import report
from . import wizard


def post_init(env):
    """Rewrite ICP's to force groups"""
    env['ir.config_parameter'].init(force=True)
