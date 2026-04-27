from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    if (rule := env.ref("approvals.approval_approver_user_unlink_own", raise_if_not_found=False)):
        rule.unlink()
    if (rule := env.ref("approvals.approval_approver_user_change_own", raise_if_not_found=False)):
        rule.unlink()
    if (rule := env.ref("approvals.approval_approver_user_create", raise_if_not_found=False)):
        rule.unlink()
