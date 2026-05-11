from odoo import api, SUPERUSER_ID

def post_init_set_home_action(env):
    action = env.ref('hr_schedule_erp.hr_schedule_servicio_action', raise_if_not_found=False)
    if not action:
        return

    users = env['res.users'].search([('share', '=', False)])
    users.write({'action_id': action.id})

def post_init_hook(env):
    post_init_set_home_action(env)