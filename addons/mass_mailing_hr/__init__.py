from . import models


# Rebind unbound action_partner_mass_mail on uninstall
def uninstall_hook(env):
    act_window = env.ref('hr.action_partner_mass_mail', raise_if_not_found=False)
    if act_window and not act_window.binding_model_id:
        act_window.binding_model_id = env['ir.model']._get_id('hr.employee')
