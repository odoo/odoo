import logging

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Asset = env["sifnext.asset"].sudo()
    Department = env["hr.department"].sudo().with_context(active_test=False)
    main_company = env.ref("base.main_company")
    fallback_by_company = {}
    mapped = 0
    fallback = 0

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

    assets = Asset.search([("owner_department_id", "=", False)])
    for asset in assets:
        company = asset.company_id or main_company
        legacy_name = (asset.owner_unit or "").strip()
        department = False
        if legacy_name:
            candidates = Department.search([("company_id", "=", company.id)])
            matches = candidates.filtered(
                lambda item: (item.name or "").strip().casefold() == legacy_name.casefold()
            )
            if len(matches) == 1:
                department = matches
                mapped += 1
        if not department:
            department = fallback_department(company)
            fallback += 1

        cr.execute(
            """
            UPDATE sifnext_asset
               SET company_id = %s, owner_department_id = %s
             WHERE id = %s
            """,
            (company.id, department.id, asset.id),
        )
        cr.execute(
            """
            UPDATE sifnext_asset_depreciation
               SET company_id = %s, department_id = %s
             WHERE asset_id = %s
            """,
            (company.id, department.id, asset.id),
        )
        asset.invalidate_recordset(["company_id", "owner_department_id"])
        journal_values = {
            "company_id": company.id,
            "department_id": department.id,
            "unit_name": department.name,
        }
        if "unit_dept" in env["sif.jurnal.entry"]._fields:
            journal_values["unit_dept"] = department.sif_journal_unit_dept
        if asset.purchase_journal_id:
            asset.purchase_journal_id.write(journal_values)
        for depreciation in asset.depreciation_ids.filtered("journal_entry_id"):
            depreciation.journal_entry_id.write(journal_values)

    _logger.info(
        "Migrated asset departments: %s exact owner-name matches, %s assigned to company fallback departments.",
        mapped,
        fallback,
    )
