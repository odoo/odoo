import logging

from odoo import SUPERUSER_ID, api
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Department = env["hr.department"].sudo().with_context(active_test=False)
    sequence = env["ir.sequence"].sudo()
    main_company = env.ref("base.main_company")

    departments_without_code = Department.search([("sif_code", "=", False)])
    for department in departments_without_code:
        code = sequence.next_by_code("sifnext.department.code")
        if not code:
            raise RuntimeError("The SIF department code sequence is missing.")
        department.write({"sif_code": code})

    cr.execute(
        """
        CREATE TABLE IF NOT EXISTS sifnext_legacy_unit_department_map (
            unit_id integer PRIMARY KEY,
            department_id integer NOT NULL
        )
        """
    )
    cr.execute("SELECT to_regclass('public.sifnext_legacy_unit_backup')")
    if cr.fetchone()[0]:
        cr.execute(
            """
            SELECT unit_id, name, code, active, company_id, journal_unit_dept
              FROM sifnext_legacy_unit_backup
             ORDER BY unit_id
            """
        )
        legacy_units = cr.fetchall()
    else:
        legacy_units = []
    mapped = 0

    for unit_id, name, code, active, company_id, journal_unit_dept in legacy_units:
        company = env["res.company"].browse(company_id).exists() if company_id else main_company
        if not company:
            raise RuntimeError("Cannot migrate legacy unit %s: its company does not exist." % unit_id)

        code = (code or "").strip().upper()
        classification = journal_unit_dept or "pusat"
        if classification not in dict(Department._fields["sif_journal_unit_dept"].selection):
            classification = "pusat"

        department = Department.search([
            ("company_id", "=", company.id),
            ("sif_code", "=", code),
        ], limit=1)
        if not department:
            same_name = Department.search([
                ("company_id", "=", company.id),
                ("name", "=", name),
            ])
            if len(same_name) > 1:
                raise RuntimeError(
                    "Cannot uniquely map legacy unit %s (%s) to an existing department." % (unit_id, name)
                )
            if same_name:
                department = same_name
                code_owner = Department.search([
                    ("company_id", "=", company.id),
                    ("sif_code", "=", code),
                    ("id", "!=", department.id),
                ], limit=1)
                if code_owner:
                    raise RuntimeError(
                        "Legacy unit code %s conflicts with department %s in company %s."
                        % (code, code_owner.display_name, company.display_name)
                    )
                department.write({
                    "sif_code": code,
                    "sif_journal_unit_dept": classification,
                })
            else:
                department = Department.create({
                    "name": name,
                    "company_id": company.id,
                    "sif_code": code,
                    "sif_journal_unit_dept": classification,
                    "active": active if active is not None else True,
                })
        else:
            department.write({"sif_journal_unit_dept": classification})

        cr.execute(
            """
            INSERT INTO sifnext_legacy_unit_department_map (unit_id, department_id)
            VALUES (%s, %s)
            ON CONFLICT (unit_id) DO UPDATE SET department_id = EXCLUDED.department_id
            """,
            (unit_id, department.id),
        )
        mapped += 1

    cr.execute(
        """
        SELECT record_id, unit_id
          FROM sifnext_legacy_unit_rel_backup
         WHERE model_name = 'res.users'
         ORDER BY record_id
        """
    )
    user_links = cr.fetchall()
    users_mapped = 0
    users_skipped = 0
    for user_id, unit_id in user_links:
        user = env["res.users"].browse(user_id).exists()
        if not user:
            continue
        if user.department_id:
            continue
        cr.execute(
            "SELECT department_id FROM sifnext_legacy_unit_department_map WHERE unit_id = %s",
            (unit_id,),
        )
        result = cr.fetchone()
        if not result:
            users_skipped += 1
            continue
        department = Department.browse(result[0]).exists()
        if department and department.company_id in user.company_ids:
            user.write({"department_id": department.id})
            users_mapped += 1
        else:
            users_skipped += 1

    _logger.info(
        "Mapped %s legacy SIF units to hr.department; assigned departments to %s users, left %s for explicit reconfiguration.",
        mapped,
        users_mapped,
        users_skipped,
    )
