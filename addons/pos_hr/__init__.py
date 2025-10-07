# -*- coding: utf-8 -*-

from . import models
from . import report
from . import wizard


def uninstall_hook(env):
    env.cr.execute("SELECT 1 FROM ir_module_module WHERE name = 'pos_hr' AND state = 'to remove'")
    if env.cr.rowcount:
        env.cr.execute("UPDATE pos_config SET module_pos_hr = False WHERE module_pos_hr")
