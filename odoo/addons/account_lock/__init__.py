# -*- coding: utf-8 -*-

from . import models
from odoo.exceptions import UserError


def uninstall_hook(env):
    if not env.ref('base.module_base').demo:
        raise UserError('The module "Irreversible Lock Date" (account_lock) cannot be uninstalled.')
