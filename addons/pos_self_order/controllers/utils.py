from werkzeug.exceptions import Unauthorized


def is_pairing_required(pos_config_sudo, request):
    if pos_config_sudo.self_ordering_mode != 'kiosk':
        return False
    if request.env.user.has_group('point_of_sale.group_pos_user'):
        return False
    return not pos_config_sudo.env['pos_self_order.kiosk.device']._get_and_touch_kiosk_device(request, pos_config_sudo.id)


def check_kiosk_access(pos_config_sudo, request):
    if is_pairing_required(pos_config_sudo, request):
        raise Unauthorized("Device not paired")
