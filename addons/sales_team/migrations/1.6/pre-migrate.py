r"""Pre-migration: ``crm.team`` favorites move onto ``mixin.user.favorite``.

``is_favorite`` is now ``is_user_favorite`` and the relation table behind
``favorite_user_ids`` is the one the ORM derives for the adopter rather than a
hand-picked name.

The mixin declares ``favorite_user_ids`` without a ``relation=``, so
``Many2many.setup_nonrelated`` names the table from the *adopter's* table:
``res_users_team_team_rel``, with columns ``team_team_id`` and
``res_users_id``. Renaming here rather than letting the schema pass create the
new table is what carries the rows: an unrenamed table is simply orphaned, and
every existing favorite silently disappears.

``is_favorite`` is ``store=False``, so no column of its own moves. What moves is
every stored artifact naming it -- and a domain naming a field the registry no
longer has raises when the domain is READ, not when the module is upgraded, so an
unrewritten filter fails later and elsewhere. Module-owned view arch is reloaded
from XML by the upgrade itself; these statements exist for the artifacts users
made.

Every statement is idempotent: the guard stops matching once a row is rewritten.
"""

OLD = "is_favorite"
NEW = "is_user_favorite"
MODEL = "team.team"

OLD_RELATION = "team_favorite_user_rel"
NEW_RELATION = "res_users_team_team_rel"
COLUMNS = (("team_id", "team_team_id"), ("user_id", "res_users_id"))


def _rewrite(expr):
    """SQL rewriting the token whole-word in ``expr``.

    :param str expr: SQL expression (column or cast) to rewrite
    :return: SQL expression with the rename applied
    :rtype: str
    """
    return rf"regexp_replace({expr}, '\y{OLD}\y', '{NEW}', 'g')"


def _matches(expr):
    """SQL guard true when ``expr`` still names the old field.

    :param str expr: SQL expression (column or cast) to test
    :return: SQL boolean expression
    :rtype: str
    """
    return rf"{expr} ~ '\y{OLD}\y'"


def _rename_relation(cr):
    """Carry the favorite rows onto the table name the mixin derives.

    ``team`` loads before this script and has already created the derived
    table, empty, whenever the database predates the rename to ``team.team``;
    the rows are then copied into it instead of renaming over it.

    :param cr: database cursor
    """
    cr.execute("SELECT to_regclass(%s)", (OLD_RELATION,))
    if not cr.fetchone()[0]:
        return
    cr.execute("SELECT to_regclass(%s)", (NEW_RELATION,))
    if not cr.fetchone()[0]:
        cr.execute(f'ALTER TABLE "{OLD_RELATION}" RENAME TO "{NEW_RELATION}"')
        for old_column, new_column in COLUMNS:
            cr.execute(
                f'ALTER TABLE "{NEW_RELATION}" RENAME COLUMN "{old_column}"'
                f' TO "{new_column}"'
            )
        return
    (old_team, new_team), (old_user, new_user) = COLUMNS
    cr.execute(
        f'INSERT INTO "{NEW_RELATION}" ("{new_team}", "{new_user}") '
        f'SELECT "{old_team}", "{old_user}" FROM "{OLD_RELATION}" '
        "ON CONFLICT DO NOTHING"
    )
    cr.execute(f'DROP TABLE "{OLD_RELATION}"')


def migrate(cr, version):
    """Rename the relation table and repoint stored domains at the new field.

    :param cr: database cursor
    :param version: installed module version; falsy on a fresh install
    """
    if not version:
        return

    _rename_relation(cr)

    cr.execute(
        f"""
        UPDATE ir_ui_view
           SET arch_db = {_rewrite("arch_db::text")}::jsonb
         WHERE {_matches("arch_db::text")}
           AND model = %s
        """,
        (MODEL,),
    )
    cr.execute(
        f"""
        UPDATE ir_filters
           SET domain = {_rewrite("domain")},
               context = {_rewrite("context")},
               sort = {_rewrite("sort")}
         WHERE ({_matches("domain")}
                OR {_matches("context")}
                OR {_matches("sort")})
           AND model_id = %s
        """,
        (MODEL,),
    )
    cr.execute(
        f"""
        UPDATE ir_act_window
           SET domain = {_rewrite("domain")},
               context = {_rewrite("context")}
         WHERE ({_matches("domain")} OR {_matches("context")})
           AND res_model = %s
        """,
        (MODEL,),
    )
