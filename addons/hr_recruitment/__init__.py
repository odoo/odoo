# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard


def uninstall_hook(env):
    if access := env.ref('hr.access_hr_job_user', raise_if_not_found=False):
        access.active = True
