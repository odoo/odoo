import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        UPDATE team_member m
           SET active = FALSE
          FROM team_team t, res_users u
         WHERE m.team_id = t.id
           AND m.user_id = u.id
           AND m.active
           AND NOT (t.active AND u.active)
     RETURNING m.id
        """
    )
    archived = cr.rowcount
    if not archived:
        return

    cr.execute(
        """
        WITH main AS (
            SELECT DISTINCT ON (m.user_id) m.user_id, m.team_id
              FROM team_member m
             WHERE m.active
             ORDER BY m.user_id, m.create_date ASC, m.id
        )
        UPDATE res_users u
           SET sale_team_id = main.team_id
          FROM main
         WHERE u.id = main.user_id
           AND u.sale_team_id IS DISTINCT FROM main.team_id
        """
    )
    repointed = cr.rowcount

    cr.execute(
        """
        UPDATE res_users u
           SET sale_team_id = NULL
         WHERE u.sale_team_id IS NOT NULL
           AND NOT EXISTS (SELECT 1
                             FROM team_member m
                            WHERE m.user_id = u.id
                              AND m.active)
        """
    )
    cleared = cr.rowcount

    _logger.info(
        "sale_team: archived %s membership(s) pointing at an archived team or "
        "salesperson; re-pointed %s and cleared %s res_users.sale_team_id",
        archived,
        repointed,
        cleared,
    )
