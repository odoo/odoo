from .constants import DEBUG_MODE_ACCESS_GROUP
from odoo.http import request


def can_enter_debug_mode(user):
    if not user:
        user_id = request.session.uid
        user = request.env['res.users'].sudo().search([('id', '=', user_id)], limit=1)
    if user.has_group(DEBUG_MODE_ACCESS_GROUP):
        return True
    return False
