import logging

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    incomes = env["pendapatan.pendapatan"].sudo().search([
        ("department_id", "=", False),
    ])
    if not incomes:
        return

    Department = env["hr.department"].sudo().with_context(active_test=False)
    fallback_by_company = {}
    mapped_count = 0
    fallback_count = 0

    for income in incomes:
        company = income.company_id
        if not company:
            raise RuntimeError(
                "Cannot migrate Pendapatan record %s: company_id is empty." % income.id
            )

        department = Department.browse()
        legacy_name = (income.unit_name or "").strip()
        if legacy_name:
            candidates = Department.search([("company_id", "=", company.id)])
            matches = candidates.filtered(
                lambda item: (item.name or "").strip().casefold() == legacy_name.casefold()
            )
            if len(matches) == 1:
                department = matches
                mapped_count += 1

        if not department:
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
                    })
                fallback_by_company[company.id] = department
            fallback_count += 1

        income.write({"department_id": department.id})
        if income.journal_id:
            income.journal_id.write({
                "company_id": company.id,
                "department_id": department.id,
                "unit_name": department.name,
            })

    _logger.info(
        "Migrated Pendapatan department: %s exact legacy-name matches, %s assigned to per-company fallback departments.",
        mapped_count,
        fallback_count,
    )
