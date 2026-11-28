from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Repair the demo role links and seed the demo attendance on existing
    databases.

    ``<function>`` elements placed in ``noupdate="1"`` data files are skipped
    during module upgrades (see ``odoo.tools.convert._tag_function``), so the
    idempotent fixes in ``res.users._fix_demo_attendance_links()`` and
    ``university.attendance._seed_attendance_demo()`` never ran for databases
    upgraded in place. Both are pure no-ops when the seeded demo records are
    absent, so running them here is safe on any database.

    Runs as a *post* migration on purpose: pre-migrations execute before the
    module's own Python code is loaded (``odoo.modules.loading``), so the
    model methods are not available to a pre-migration script.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["res.users"]._fix_demo_attendance_links()
    env["university.attendance"]._seed_attendance_demo()