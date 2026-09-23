import logging

from odoo.addons.base.models.ir_access_convert import rewrite_converted_domain

_logger = logging.getLogger(__name__)

REQUEST_DOMAIN = (
    "[\n"
    "                '|', '|',\n"
    "                ('request_owner_id', '=', user.id),\n"
    "                ('approver_ids.user_id', '=', user.id),\n"
    "                ('approver_ids.delegate_id', '=', user.id)\n"
    "            ]"
)


def migrate(cr, version):
    cr.execute(
        """
        ALTER TABLE approval_request
        DROP COLUMN IF EXISTS quick_approve_token,
        DROP COLUMN IF EXISTS quick_approve_expires_at,
        DROP COLUMN IF EXISTS quick_approve_url,
        DROP COLUMN IF EXISTS qr_code
        """,
    )

    cr.execute(
        """
        ALTER TABLE approval_category
        DROP COLUMN IF EXISTS quick_approve_ttl_hours
        """,
    )

    cr.execute(
        """
        DELETE FROM ir_config_parameter
        WHERE key = 'approval.quick_approve.secret'
        """,
    )
    secret_dropped = cr.rowcount

    for name, label in (
        (
            "approval_request_user_read",
            "Approval Request: user read own or approver or delegate",
        ),
        (
            "approval_request_user_write",
            "Approval Request: user write own or approver or delegate",
        ),
    ):
        rewrite_converted_domain(cr, "approval", name, REQUEST_DOMAIN, logger=_logger)
        cr.execute(
            """
            UPDATE ir_access a SET name = %s
              FROM ir_model_data d
             WHERE d.model = 'ir.access' AND d.res_id = a.id
               AND d.module = 'approval' AND d.name = %s
            """,
            (label, name),
        )

    cr.execute(
        """
        UPDATE mail_activity
        SET note = NULL
        WHERE active = true
          AND note LIKE %s
        """,
        ("%/approval/quick/%",),
    )
    activities_cleaned = cr.rowcount

    _logger.info(
        "t22503: dropped quick_approve columns + %d secret(s); "
        "cleaned note on %d open mail.activity records.",
        secret_dropped,
        activities_cleaned,
    )
