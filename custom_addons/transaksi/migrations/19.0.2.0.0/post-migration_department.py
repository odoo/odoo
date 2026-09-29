import logging

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)


def _table_exists(cr, table_name):
    cr.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
    return bool(cr.fetchone()[0])


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Transaction = env["transaksi.transaction"].sudo()
    Department = env["hr.department"].sudo().with_context(active_test=False)
    main_company = env.ref("base.main_company")
    fallback_by_company = {}

    legacy_links = {}
    if _table_exists(cr, "sifnext_legacy_unit_rel_backup"):
        cr.execute(
            """
            SELECT record_id, unit_id
              FROM sifnext_legacy_unit_rel_backup
             WHERE model_name = 'transaksi.transaction'
            """
        )
        legacy_links = dict(cr.fetchall())

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

    mapped = 0
    fallback = 0
    mixed_ppl = 0
    for transaction in Transaction.search([("department_id", "=", False)]):
        company = transaction.company_id or main_company
        department = False
        old_unit_id = legacy_links.get(transaction.id)
        if old_unit_id and _table_exists(cr, "sifnext_legacy_unit_department_map"):
            cr.execute(
                "SELECT department_id FROM sifnext_legacy_unit_department_map WHERE unit_id = %s",
                (old_unit_id,),
            )
            mapping = cr.fetchone()
            if mapping:
                department = Department.browse(mapping[0]).exists()

        related_ppls = transaction.ppl_id | transaction.ppl_ids | transaction.line_ids.mapped("ppl_id")
        if any(ppl.company_id != company for ppl in related_ppls):
            raise RuntimeError(
                "Cannot migrate bank transfer %s: linked PPL documents belong to different companies."
                % transaction.id
            )
        if not department and related_ppls:
            departments = related_ppls.mapped("department_id")
            if len(departments) == 1:
                department = departments
            elif len(departments) > 1:
                mixed_ppl += 1
                continue

        if department and department.company_id == company:
            mapped += 1
        else:
            department = fallback_department(company)
            fallback += 1

        cr.execute(
            "UPDATE transaksi_transaction SET department_id = %s WHERE id = %s",
            (department.id, transaction.id),
        )

    if _table_exists(cr, "transaksi_transaction"):
        cr.execute("ALTER TABLE transaksi_transaction DROP COLUMN IF EXISTS unit_id")

    if _table_exists(cr, "sifnext_unit"):
        if not _table_exists(cr, "sifnext_legacy_unit_backup"):
            raise RuntimeError(
                "Cannot remove sifnext_unit: the legacy unit backup table is missing."
            )
        cr.execute(
            """
            SELECT COUNT(*)
              FROM sifnext_unit AS legacy
              LEFT JOIN sifnext_legacy_unit_backup AS backup
                ON backup.unit_id = legacy.id
             WHERE backup.unit_id IS NULL
            """
        )
        unbacked_units = cr.fetchone()[0]
        if unbacked_units:
            raise RuntimeError(
                "Cannot remove sifnext_unit: %s legacy units are not backed up."
                % unbacked_units
            )
        cr.execute("DROP TABLE sifnext_unit")
        _logger.info("Removed legacy sifnext_unit table after department migration.")

    _logger.info(
        "Migrated bank-transfer departments: %s mapped, %s assigned to company fallback, %s mixed-PPL headers kept without one department.",
        mapped,
        fallback,
        mixed_ppl,
    )
