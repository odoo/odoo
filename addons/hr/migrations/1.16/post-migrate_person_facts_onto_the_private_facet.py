import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# The employee's column -> the field it becomes on the private facet.
COLUMNS = {
    "place_of_birth": "place_of_birth",
    "country_of_birth": "country_of_birth",
    "marital": "marital",
    "spouse_complete_name": "spouse_complete_name",
    "spouse_birthdate": "spouse_birthdate",
    "children": "dependent_children",
    "certificate": "education_certificate",
    "study_field": "study_field",
    "study_school": "study_school",
}


def migrate(cr, version):
    if not version:
        return
    columns = list(COLUMNS)
    cr.execute(
        f"SELECT id, {', '.join(columns)} FROM hr_employee WHERE "
        + " OR ".join(f"{column} IS NOT NULL" for column in columns)
    )
    rows = cr.fetchall()
    if rows:
        env = api.Environment(cr, SUPERUSER_ID, {})
        employees = (
            env["hr.employee"]
            .with_context(active_test=False)
            .browse([row[0] for row in rows])
        )
        # Give every employee that carries one of these values a facet to put
        # it on; an employee with no party at all keeps its columns and is
        # counted, because there is nothing to hang a facet from.
        employees._compute_private_address_id()
        facets = {employee.id: employee.private_address_id for employee in employees}
        moved = skipped = 0
        for employee_id, *values in rows:
            facet = facets[employee_id]
            if not facet:
                skipped += 1
                continue
            facet.write(
                {
                    target: value
                    for (column, target), value in zip(
                        COLUMNS.items(), values, strict=True
                    )
                    if value is not None
                }
            )
            moved += 1
        _logger.info(
            "person facts moved onto the private facet for %s employees, "
            "%s employees without a party kept theirs in the old columns",
            moved,
            skipped,
        )
    cr.execute(
        "ALTER TABLE hr_employee "
        + ", ".join(f"DROP COLUMN IF EXISTS {column}" for column in columns)
    )
