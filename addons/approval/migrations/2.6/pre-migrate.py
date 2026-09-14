from odoo import SUPERUSER_ID, api
from odoo.tools import SQL

_FORM_MODELS = ["approval.template", "approval.document.requirement"]

_FORM_FIELDS = [
    *(
        f"approval.category.{name}"
        for name in (
            "has_date",
            "has_date_deadline",
            "has_date_planned",
            "has_date_range",
            "has_partner",
            "has_quantity",
            "has_amount",
            "has_reference",
            "has_location",
            "has_document",
            "document_requirement_ids",
            "template_count",
        )
    ),
    *(
        f"approval.request.{name}"
        for name in (
            "date_deadline",
            "date_planned",
            "location",
            "reference",
            "has_date",
            "has_date_deadline",
            "has_date_planned",
            "has_date_range",
            "has_quantity",
            "has_amount",
            "has_reference",
            "has_partner",
            "has_location",
            "has_document",
            "document_requirement_ids",
            "template_id",
        )
    ),
    "ir.attachment.approval_requirement_id",
]

_FORM_RECORDS = [
    "access_approval_document_requirement",
    "access_approval_document_requirement_manager",
    "access_approval_template",
    "access_approval_template_manager",
    "action_approval_template",
    "approval_template_rule",
    "view_approval_document_requirement_list",
    "view_approval_template_form",
    "view_approval_template_list",
    "view_approval_template_search",
]

_FORM_FOREIGN_KEYS = [
    "approval_request_template_id_fkey",
    "ir_attachment_approval_requirement_id_fkey",
]


def _form_is_in_use(cr):
    cr.execute(
        """
        SELECT EXISTS (SELECT 1 FROM approval_template)
            OR EXISTS (SELECT 1 FROM approval_document_requirement)
            OR EXISTS (
                SELECT 1
                  FROM approval_request
                 WHERE date_deadline IS NOT NULL
                    OR date_planned IS NOT NULL
                    OR location IS NOT NULL
                    OR reference IS NOT NULL
            )
        """
    )
    return cr.fetchone()[0]


def _ensure_the_app_loads(cr):
    cr.execute("SELECT state FROM ir_module_module WHERE name = 'approval_app'")
    row = cr.fetchone()
    if row and row[0] in ("installed", "to upgrade", "to install"):
        return True
    if not _form_is_in_use(cr):
        return False
    if not row:
        api.Environment(cr, SUPERUSER_ID, {})["ir.module.module"].update_list()
    cr.execute(
        """
        UPDATE ir_module_module AS app
           SET state = 'to install',
               demo = engine.demo
          FROM ir_module_module AS engine
         WHERE app.name = 'approval_app'
           AND engine.name = 'approval'
        """
    )
    return True


def _release_category_flag_columns(cr):
    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_name = 'approval_category'
           AND column_name LIKE 'has\\_%%'
           AND is_nullable = 'NO'
        """
    )
    for (column,) in cr.fetchall():
        cr.execute(
            SQL(
                "ALTER TABLE approval_category ALTER COLUMN %s DROP NOT NULL",
                SQL.identifier(column),
            )
        )


def migrate(cr, version):
    _release_category_flag_columns(cr)
    if not _ensure_the_app_loads(cr):
        cr.execute(
            "DROP TABLE IF EXISTS approval_template, approval_document_requirement CASCADE"
        )
        return
    cr.execute(
        """
        WITH engine AS (
            SELECT id FROM ir_module_module WHERE name = 'approval'
        ), app AS (
            SELECT id FROM ir_module_module WHERE name = 'approval_app'
        ), form_models AS (
            SELECT id FROM ir_model WHERE model = ANY(%(models)s)
        ), form_fields AS (
            SELECT id
              FROM ir_model_fields
             WHERE model = ANY(%(models)s)
                OR model || '.' || name = ANY(%(fields)s)
        ), form_constraints AS (
            UPDATE ir_model_constraint
               SET module = (SELECT id FROM app)
             WHERE module = (SELECT id FROM engine)
               AND (
                   model IN (SELECT id FROM form_models)
                   OR name = ANY(%(foreign_keys)s)
               )
         RETURNING id
        ), form_relations AS (
            UPDATE ir_model_relation
               SET module = (SELECT id FROM app)
             WHERE module = (SELECT id FROM engine)
               AND model IN (SELECT id FROM form_models)
        )
        UPDATE ir_model_data
           SET module = 'approval_app'
         WHERE module = 'approval'
           AND (
               name = ANY(%(records)s)
               OR (model = 'ir.model' AND res_id IN (SELECT id FROM form_models))
               OR (model = 'ir.model.fields' AND res_id IN (SELECT id FROM form_fields))
               OR (
                   model = 'ir.model.fields.selection'
                   AND res_id IN (
                       SELECT id
                         FROM ir_model_fields_selection
                        WHERE field_id IN (SELECT id FROM form_fields)
                   )
               )
               OR (
                   model = 'ir.model.constraint'
                   AND res_id IN (SELECT id FROM form_constraints)
               )
               OR (
                   model = 'ir.model.inherit'
                   AND res_id IN (
                       SELECT id
                         FROM ir_model_inherit
                        WHERE model_id IN (SELECT id FROM form_models)
                   )
               )
           )
        """,
        {
            "models": _FORM_MODELS,
            "fields": _FORM_FIELDS,
            "records": _FORM_RECORDS,
            "foreign_keys": _FORM_FOREIGN_KEYS,
        },
    )
