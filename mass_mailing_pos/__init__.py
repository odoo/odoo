

# Rebind unbound model_pos_order_send_mail on uninstall
def uninstall_hook(env):
    act_window = env.ref('point_of_sale.model_pos_order_send_mail', raise_if_not_found=False)
    if act_window and not act_window.binding_model_id:
        act_window.binding_model_id = env['ir.model']._get_id('pos.order')
