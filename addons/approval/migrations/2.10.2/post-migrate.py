from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "approval_approver", ["company_id"])
    schema.drop_columns(cr, "approval_binding", ["model_name"])
    schema.drop_columns(cr, "approval_category_step", ["company_id"])
    schema.drop_columns(cr, "approval_category_step_member", ["company_id"])
    schema.drop_columns(cr, "approval_decision_log", ["company_id"])
    schema.drop_columns(cr, "approval_request", ["approval_type", "target_model"])
