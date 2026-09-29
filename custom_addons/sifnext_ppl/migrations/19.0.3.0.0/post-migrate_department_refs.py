import logging

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)


def _table_exists(cr, table_name):
    cr.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
    return bool(cr.fetchone()[0])


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Department = env["hr.department"].sudo().with_context(active_test=False)
    PPL = env["sifnext.ppl"].sudo()
    main_company = env.ref("base.main_company")
    fallback_by_company = {}

    def fallback_department(company):
        department = fallback_by_company.get(company.id)
        if not department:
            department = Department.search([
                ("company_id", "=", company.id),
                ("name", "=", "Belum Diklasifikasikan"),
            ], limit=1)
            if not department:
                department = Department.create({
                    "name": "Belum Diklasifikasikan",
                    "company_id": company.id,
                    "sif_journal_unit_dept": "pusat",
                })
            fallback_by_company[company.id] = department
        return department

    unit_map_exists = _table_exists(cr, "sifnext_legacy_unit_department_map")
    legacy_links = {}
    if _table_exists(cr, "sifnext_legacy_unit_rel_backup"):
        cr.execute(
            """
            SELECT record_id, unit_id
              FROM sifnext_legacy_unit_rel_backup
             WHERE model_name = 'sifnext.ppl'
            """
        )
        legacy_links = dict(cr.fetchall())

    mapped = 0
    fallback = 0
    for ppl in PPL.search([("department_id", "=", False)]):
        company = ppl.company_id or main_company
        department = False
        old_unit_id = legacy_links.get(ppl.id)
        if old_unit_id and unit_map_exists:
            cr.execute(
                "SELECT department_id FROM sifnext_legacy_unit_department_map WHERE unit_id = %s",
                (old_unit_id,),
            )
            mapping = cr.fetchone()
            if mapping:
                department = Department.browse(mapping[0]).exists()
        if department and department.company_id != company:
            department = False
        if department:
            mapped += 1
        else:
            department = fallback_department(company)
            fallback += 1
        # Raw SQL avoids the PPL write guard on submitted or completed legacy records.
        cr.execute(
            "UPDATE sifnext_ppl SET department_id = %s WHERE id = %s",
            (department.id, ppl.id),
        )

    if _table_exists(cr, "custom_payroll_batch"):
        cr.execute(
            """
            UPDATE sifnext_ppl AS ppl
               SET payroll_batch_id = batch.id
              FROM custom_payroll_batch AS batch
             WHERE batch.ppl_id = ppl.id
               AND ppl.payroll_batch_id IS NULL
            """
        )

    cr.execute(
        "DELETE FROM ir_model_data WHERE module = 'sifnext_ppl' AND name = 'unit_uat_ppl'"
    )

    obsolete_records = {
        "ir.ui.menu": ["menu_sifnext_unit"],
        "ir.ui.view": [
            "view_sifnext_unit_list",
            "view_sifnext_unit_form",
            "view_users_form_sifnext_unit",
        ],
        "ir.actions.act_window": ["action_sifnext_unit"],
        "ir.rule": ["unit_company_rule"],
        "ir.model.access": ["access_sifnext_unit_user", "access_sifnext_unit_finance"],
    }
    for model_name, xmlids in obsolete_records.items():
        for xmlid in xmlids:
            record = env.ref("sifnext_ppl.%s" % xmlid, raise_if_not_found=False)
            if record and record.exists():
                record.unlink()

    if _table_exists(cr, "res_users"):
        cr.execute("ALTER TABLE res_users DROP COLUMN IF EXISTS unit_id")
    if _table_exists(cr, "sifnext_ppl"):
        cr.execute("ALTER TABLE sifnext_ppl DROP COLUMN IF EXISTS unit_id")

    _logger.info(
        "Migrated PPL department references: %s from legacy units and %s to fallback departments.",
        mapped,
        fallback,
    )
