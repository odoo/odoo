# -*- coding: utf-8 -*-


import werkzeug

from odoo.http import request
from odoo.addons.pos_self_order.models.pos_config import PosConfig

def get_any_pos_config_sudo() -> PosConfig:
    """
    Returns a PosConfig that allows the QR code menu, if there is one,
    or raises a NotFound otherwise
    """
    return (
        request.env["pos.config"].sudo().search([('|'), ("self_order_view_mode", "=", True), ("self_order_kiosk", "=", True)], limit=1)
    ) or _raise(werkzeug.exceptions.NotFound())

def _raise(e):
    raise e

def reduce_privilege(record_sudo, company, user=None):
    """
    Returns a record with reduced privileges based on company and user.
    If user is not provided, we keep the sudo privilege, but still, the record
    will be scoped to the company.
    """
    if record_sudo:
        if user:
            return record_sudo.sudo(False).with_company(company).with_user(user)
        else:
            return record_sudo.with_company(company)
    return None
