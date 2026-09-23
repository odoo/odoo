import logging

from odoo.addons.base.models.ir_access_convert import rewrite_converted_domain

_logger = logging.getLogger(__name__)

NEW_DOMAIN = (
    "[\n"
    "    '|', '|', '|',\n"
    "    ('request_id.request_owner_id', '=', user.id),\n"
    "    ('user_id', '=', user.id),\n"
    "    ('delegate_id', '=', user.id),\n"
    "    ('request_id.approver_ids.user_id', '=', user.id)\n"
    "]"
)
NEW_NAME = "Approval Approver: user read own request, self, delegated, or co-approver"


def migrate(cr, version):
    rewrite_converted_domain(
        cr, "approval", "approval_approver_user_read", NEW_DOMAIN, logger=_logger
    )
    cr.execute(
        """
        UPDATE ir_access a
        SET name = %s
        FROM ir_model_data d
        WHERE d.model = 'ir.access' AND d.res_id = a.id
          AND d.module = 'approval' AND d.name = 'approval_approver_user_read'
        """,
        (NEW_NAME,),
    )

    cr.execute(
        """
        UPDATE approval_category_approver aca
        SET company_id = ac.company_id
        FROM approval_category ac
        WHERE ac.id = aca.category_id
          AND aca.company_id IS DISTINCT FROM ac.company_id
        """,
    )
    if cr.rowcount:
        _logger.info(
            "19.0.1.0.10: backfilled company_id on %d category-approver row(s).",
            cr.rowcount,
        )
