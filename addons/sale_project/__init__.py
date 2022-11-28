# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.api import SUPERUSER_ID, Environment
from odoo.http import request
from odoo.models import BaseModel

from . import controllers, models, report


def post_init_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    user = env.user
    if has_groups(user, 'project.group_project_milestone'):
        env['ir.config_parameter'].sudo().set_param('display_milestones_policy', 'True')



def has_groups(user, groups):
    has_groups = []
    not_has_groups = []
    for group_ext_id in groups.split(','):
        group_ext_id = group_ext_id.strip()
        if group_ext_id[0] == '!':
            not_has_groups.append(group_ext_id[1:])
        else:
            has_groups.append(group_ext_id)

    for group_ext_id in not_has_groups:
        if group_ext_id == 'base.group_no_one':
            # check: the group_no_one is effective in debug mode only
            if user.has_group(group_ext_id) and request and request.session.debug:
                return False
        else:
            if user.has_group(group_ext_id):
                return False

    for group_ext_id in has_groups:
        if group_ext_id == 'base.group_no_one':
            # check: the group_no_one is effective in debug mode only
            if user.has_group(group_ext_id) and request and request.session.debug:
                return True
        else:
            if user.has_group(group_ext_id):
                return True

    return not has_groups

    
