"""Reject upgrades until legacy duplicate academic-year names are resolved."""


def migrate(cr, version):
    cr.execute(
        "SELECT to_regclass('public.university_academic_year') IS NOT NULL"
    )
    if not cr.fetchone()[0]:
        return

    cr.execute(
        """
        SELECT name, array_agg(id ORDER BY id)
        FROM university_academic_year
        WHERE name IS NOT NULL
        GROUP BY name
        HAVING count(*) > 1
        ORDER BY name
        """
    )
    duplicates = cr.fetchall()
    if not duplicates:
        return

    details = "; ".join(
        "%r (IDs: %s)" % (name, ", ".join(map(str, ids)))
        for name, ids in duplicates
    )
    raise RuntimeError(
        "Cannot upgrade school_management until duplicate academic-year names "
        "are resolved. Rename or merge the affected records intentionally, "
        "then retry. Duplicates: %s" % details
    )
