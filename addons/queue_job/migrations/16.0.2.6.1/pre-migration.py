# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo.tools.sql import table_exists


def migrate(cr, version):
    if table_exists(cr, "queue_job"):
        # Drop index 'queue_job_identity_key_state_partial_index',
        # it will be recreated during the update
        cr.execute("DROP INDEX IF EXISTS queue_job_identity_key_state_partial_index;")
