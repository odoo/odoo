# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

from . import models
from . import wizard


def uninstall_hook(env):
    group_show_job_id = env.ref('hr_recruitment.group_show_job_id')
    group_user = env.ref('base.group_user')
    group_show_job_id.implied_by_ids = [Command.unlink(group_user.id)]
