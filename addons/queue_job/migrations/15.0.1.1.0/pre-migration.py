# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo.tools.sql import column_exists, table_exists


def migrate(cr, version):
    if table_exists(cr, "queue_job") and not column_exists(
        cr, "queue_job", "exec_time"
    ):
        # Disable trigger otherwise the update takes ages.
        cr.execute(
            """
            ALTER TABLE queue_job DISABLE TRIGGER queue_job_notify;
        """
        )
        cr.execute(
            """
            ALTER TABLE queue_job ADD COLUMN exec_time double precision DEFAULT 0;
        """
        )
        cr.execute(
            """
            UPDATE
                queue_job
            SET
                exec_time = EXTRACT(EPOCH FROM (date_done - date_started));
        """
        )
        cr.execute(
            """
            ALTER TABLE queue_job ENABLE TRIGGER queue_job_notify;
        """
        )
