import logging

from odoo.addons.base.models.ir_access_convert import rewrite_converted_domain

_logger = logging.getLogger(__name__)

NEW_DOMAIN = (
    "[\n"
    "    '|', '|', '|', '|',\n"
    "    ('request_id.request_owner_id', '=', user.id),\n"
    "    ('user_id', '=', user.id),\n"
    "    ('delegate_id', '=', user.id),\n"
    "    ('request_id.approver_ids.user_id', '=', user.id),\n"
    "    ('request_id.approver_ids.delegate_id', '=', user.id)\n"
    "]"
)


def migrate(cr, version):
    rewrite_converted_domain(
        cr, "approval", "approval_approver_user_read", NEW_DOMAIN, logger=_logger
    )
