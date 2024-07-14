# -*- coding: utf-8 -*-

from . import models
from . import wizard
from . import report


def pre_init_hook(env):
    root_menu = env.ref('hr_timesheet.timesheet_menu_root', raise_if_not_found=False)
    if root_menu and not root_menu.active:
        root_menu.write({'active': True})

def post_init_hook(env):
    companies = env['res.company'].search([('timesheet_mail_employee_nextdate', '=', False), ('timesheet_mail_nextdate', '=', False)])
    companies._calculate_timesheet_mail_employee_nextdate()
    companies._calculate_timesheet_mail_nextdate()

def uninstall_hook(env):
    """
    Unfortunately, the grid view is defined in enterprise, and the
    timesheet actions (community) are inherited in enterprise to
    add the grid view in the view_modes.
    As they override view_mode directly instead of creating
    ir.actions.act_window.view that would be unlinked properly
    when uninstalling timesheet_grid, here we clean the view_mode
    manually.
    """
    root_menu = env.ref('hr_timesheet.timesheet_menu_root', raise_if_not_found=False)
    if root_menu and root_menu.active:
        root_menu.write({'active': False})

    actions = env['ir.actions.act_window'].search([
        ('res_model', '=', 'account.analytic.line')
    ]).filtered(
        lambda action: action.xml_id.startswith('hr_timesheet.') and 'grid' in action.view_mode)
    for action in actions:
        action.view_mode = ','.join(view_mode for view_mode in action.view_mode.split(',') if view_mode != 'grid')

    # revert module override of external view inherit_id
    inherit_ids = {
        'hr_timesheet.hr_timesheet_line_my_timesheet_search': 'hr_timesheet.hr_timesheet_line_search',
    }
    for view_xid, inherit_xid in inherit_ids.items():
        view = env.ref(view_xid, raise_if_not_found=False)
        inherit = env.ref(inherit_xid, raise_if_not_found=False)
        if view and inherit:
            view.inherit_id = inherit
