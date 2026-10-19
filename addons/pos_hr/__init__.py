# -*- coding: utf-8 -*-

from . import models
from . import report
from . import wizard


def uninstall_hook(env):
    env['pos.config'].search([('module_pos_hr', '=', True)]).module_pos_hr = False
