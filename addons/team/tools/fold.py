import ast
import logging

from odoo.db.schema import TableKind, column_exists, get_table_kind, table_exists
from odoo.tools import SQL
from odoo.tools.module_data import (
    rename_in_stored_expressions,
    rewrite_quoted_model_names,
)

_logger = logging.getLogger(__name__)

TEAM_MODEL = "team.team"
TEAM_TABLE = "team_team"
MAP_TABLE = "team_fold_map"
MODEL_ID_PAIRS = (
    ("model", "res_id"),
    ("res_model", "res_id"),
    ("parent_res_model", "parent_res_id"),
)
MODEL_NAME_COLUMNS = (
    ("mail_message_subtype", "res_model"),
    ("ir_act_window", "res_model"),
    ("ir_ui_view", "model"),
    ("ir_filters", "model_id"),
    ("mail_activity_type", "res_model"),
    ("ir_embedded_actions", "parent_res_model"),
)
CORE_COLUMNS = (
    "name",
    "active",
    "company_id",
    "color",
    "sequence",
    "description",
    "create_uid",
    "create_date",
    "write_uid",
    "write_date",
)


def fold_team_model(
    cr,
    old_model,
    flag,
    *,
    renamed=None,
    members=None,
    alias_usage=None,
    alias_team_field="team_id",
    links=("team_id",),
):
    """Make every row of ``old_model`` a ``team.team`` flagged ``flag``.

    Runs in the pre-migration of the module that owned ``old_model``, before its
    fields are declared on ``team.team``: every reference is repointed while
    the old ids can still be told from the new ones, so the foreign keys the
    ORM re-creates validate. Columns the old table carries beyond the core are
    copied onto ``team_team`` under ``renamed``'s name, for the modules that now
    declare them to adopt. ``members`` names the many2many table and user
    column whose rows become ``team.member`` rows. ``alias_usage`` turns the
    old ``alias_id`` column into that usage's ``team.alias`` row, whose defaults
    name the team under ``alias_team_field``. ``links`` are the many2one fields
    through which stored expressions (rules, templates, filters) reach the
    team, so ``links[i].<old field>`` is rewritten to the renamed field.
    """
    old_table = old_model.replace(".", "_")
    if not table_exists(cr, old_table):
        return {}
    renamed = dict(renamed or {})
    cr.execute(
        SQL(
            "ALTER TABLE team_team ADD COLUMN IF NOT EXISTS %s boolean",
            SQL.identifier(flag),
        )
    )
    cr.execute(
        SQL(
            "CREATE TABLE IF NOT EXISTS %s (old_model varchar, old_id int, new_id int)",
            SQL.identifier(MAP_TABLE),
        )
    )
    mapping = _insert_teams(cr, old_model, old_table, flag)
    if alias_usage:
        _fold_alias(cr, old_model, old_table, alias_usage, alias_team_field)
        renamed.setdefault("alias_id", None)
    _copy_columns(cr, old_model, old_table, renamed)
    if members:
        _fold_members(cr, old_model, old_table, *members)
    _rename_relation_tables(cr, old_model, old_table)
    # tracking values find their fields by relation, which _repoint_relations moves
    _repoint_tracking(cr, old_model)
    _repoint_relations(cr, old_model, old_table)
    _repoint_records(cr, old_model)
    _repoint_model_ids(cr, old_model)
    _move_registry_rows(cr, old_model, old_table, renamed)
    _rewrite_expressions(cr, old_model, renamed, links)
    cr.execute(SQL("DROP TABLE %s CASCADE", SQL.identifier(old_table)))
    _logger.info(
        "team: %d %s record(s) folded into team.team as %s",
        len(mapping),
        old_model,
        flag,
    )
    return mapping


def get_folded_id(cr, old_model, old_id):
    cr.execute(
        SQL(
            "SELECT new_id FROM %s WHERE old_model = %s AND old_id = %s",
            SQL.identifier(MAP_TABLE),
            old_model,
            old_id,
        )
    )
    row = cr.fetchone()
    return row[0] if row else None


def _column_types(cr, table):
    cr.execute(
        SQL(
            """
            SELECT a.attname, format_type(a.atttypid, a.atttypmod)
              FROM pg_attribute a
             WHERE a.attrelid = %s::regclass AND a.attnum > 0 AND NOT a.attisdropped
            """,
            table,
        )
    )
    return dict(cr.fetchall())


def _insert_teams(cr, old_model, old_table, flag):
    old_columns = _column_types(cr, old_table)
    team_columns = _column_types(cr, TEAM_TABLE)
    selected, targets = [], []
    for column in CORE_COLUMNS:
        if column not in old_columns or column not in team_columns:
            continue
        expression = SQL.identifier(column)
        if team_columns[column] == "jsonb" and old_columns[column] != "jsonb":
            expression = SQL("jsonb_build_object('en_US', %s)", SQL.identifier(column))
        selected.append(expression)
        targets.append(SQL.identifier(column))
    defaults = {"active": SQL("true"), "sequence": SQL("10")}
    for column, value in defaults.items():
        if column not in old_columns:
            selected.append(value)
            targets.append(SQL.identifier(column))
    cr.execute(SQL("SELECT id FROM %s ORDER BY id", SQL.identifier(old_table)))
    mapping = {}
    for (old_id,) in cr.fetchall():
        cr.execute(
            SQL(
                "INSERT INTO team_team (%s, %s) SELECT %s, true FROM %s WHERE id = %s RETURNING id",
                SQL(", ").join(targets),
                SQL.identifier(flag),
                SQL(", ").join(selected),
                SQL.identifier(old_table),
                old_id,
            )
        )
        mapping[old_id] = cr.fetchone()[0]
    for old_id, new_id in mapping.items():
        cr.execute(
            SQL(
                "INSERT INTO %s (old_model, old_id, new_id) VALUES (%s, %s, %s)",
                SQL.identifier(MAP_TABLE),
                old_model,
                old_id,
                new_id,
            )
        )
    return mapping


def _fold_alias(cr, old_model, old_table, usage, team_field):
    if not column_exists(cr, old_table, "alias_id"):
        return
    cr.execute(
        SQL(
            """
            INSERT INTO team_alias (team_id, usage, alias_id,
                                    create_uid, create_date, write_uid, write_date)
            SELECT m.new_id, %s, o.alias_id, 1, now() AT TIME ZONE 'UTC',
                   1, now() AT TIME ZONE 'UTC'
              FROM %s o
              JOIN %s m ON m.old_model = %s AND m.old_id = o.id
             WHERE o.alias_id IS NOT NULL
            RETURNING team_id, alias_id
            """,
            usage,
            SQL.identifier(old_table),
            SQL.identifier(MAP_TABLE),
            old_model,
        )
    )
    # mail to the alias creates records with these defaults: they name the old id
    for team_id, alias_id in cr.fetchall():
        cr.execute(SQL("SELECT alias_defaults FROM mail_alias WHERE id = %s", alias_id))
        defaults = ast.literal_eval(cr.fetchone()[0] or "{}")
        defaults[team_field] = team_id
        cr.execute(
            SQL(
                "UPDATE mail_alias SET alias_defaults = %s WHERE id = %s",
                repr(defaults),
                alias_id,
            )
        )


def _copy_columns(cr, old_model, old_table, renamed):
    old_columns = _column_types(cr, old_table)
    team_columns = _column_types(cr, TEAM_TABLE)
    skipped = {"id", *CORE_COLUMNS}
    for column, column_type in old_columns.items():
        if column in skipped:
            continue
        target = renamed.get(column, column)
        if target is None:
            continue
        if target not in team_columns:
            cr.execute(
                SQL(
                    "ALTER TABLE team_team ADD COLUMN %s %s",
                    SQL.identifier(target),
                    SQL(column_type),
                )
            )
        cr.execute(
            SQL(
                """
                UPDATE team_team t SET %s = o.%s
                  FROM %s o JOIN %s m ON m.old_model = %s AND m.old_id = o.id
                 WHERE t.id = m.new_id
                """,
                SQL.identifier(target),
                SQL.identifier(column),
                SQL.identifier(old_table),
                SQL.identifier(MAP_TABLE),
                old_model,
            )
        )


def _drop_foreign_keys(cr, table, column, referenced):
    cr.execute(
        SQL(
            """
            SELECT c.conname
              FROM pg_constraint c
              JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
             WHERE c.contype = 'f' AND c.conrelid = %s::regclass
               AND c.confrelid = %s::regclass AND a.attname = %s
            """,
            table,
            referenced,
            column,
        )
    )
    for (name,) in cr.fetchall():
        cr.execute(
            SQL(
                "ALTER TABLE %s DROP CONSTRAINT %s",
                SQL.identifier(table),
                SQL.identifier(name),
            )
        )


def _remap_column(cr, old_model, table, column):
    # Old and new ids overlap whenever team_team already holds ids beyond the
    # smallest old one, so a one-pass UPDATE can move a row twice or collide on a
    # relation table's primary key: park the new ids negative, then flip them.
    cr.execute(
        SQL(
            """
            UPDATE %s x SET %s = -m.new_id
              FROM %s m
             WHERE m.old_model = %s AND x.%s = m.old_id
            """,
            SQL.identifier(table),
            SQL.identifier(column),
            SQL.identifier(MAP_TABLE),
            old_model,
            SQL.identifier(column),
        )
    )
    cr.execute(
        SQL(
            "UPDATE %s SET %s = -%s WHERE %s < 0",
            SQL.identifier(table),
            SQL.identifier(column),
            SQL.identifier(column),
            SQL.identifier(column),
        )
    )


def _repoint_relations(cr, old_model, old_table):
    cr.execute(
        SQL(
            """
            SELECT model, name, ttype, relation_table, column1, column2, relation
              FROM ir_model_fields
             WHERE store AND ttype IN ('many2one', 'many2many')
               AND (relation = %s OR (model = %s AND ttype = 'many2many'))
            """,
            old_model,
            old_model,
        )
    )
    remapped = set()
    for model, name, ttype, relation_table, column1, column2, relation in cr.fetchall():
        if ttype == "many2one":
            table = model.replace(".", "_")
            if (
                model == old_model
                or get_table_kind(cr, table) != TableKind.Regular
                or not column_exists(cr, table, name)
            ):
                continue
            target = (table, name)
        else:
            if (
                not relation_table
                or get_table_kind(cr, relation_table) != TableKind.Regular
            ):
                continue
            column = column1 if model == old_model else column2
            if relation == old_model and model != old_model:
                column = column2
            table, name, target = relation_table, column, (relation_table, column)
        if target in remapped:
            continue
        remapped.add(target)
        _drop_foreign_keys(cr, table, name, old_table)
        _remap_column(cr, old_model, table, name)
    cr.execute(
        SQL(
            "UPDATE ir_model_fields SET relation = %s WHERE relation = %s",
            TEAM_MODEL,
            old_model,
        )
    )


def _repoint_records(cr, old_model):
    cr.execute(
        """
        SELECT c.table_name, c.column_name
          FROM information_schema.columns c
          JOIN information_schema.tables t
            ON t.table_schema = c.table_schema AND t.table_name = c.table_name
         WHERE c.table_schema = current_schema() AND t.table_type = 'BASE TABLE'
           AND c.data_type IN ('character varying', 'text')
        """
    )
    text_columns = {}
    for table, column in cr.fetchall():
        text_columns.setdefault(table, set()).add(column)
    for table, columns in text_columns.items():
        for model_column, id_column in MODEL_ID_PAIRS:
            if model_column not in columns or not column_exists(cr, table, id_column):
                continue
            cr.execute(
                SQL(
                    """
                    UPDATE %s x SET %s = %s, %s = m.new_id
                      FROM %s m
                     WHERE x.%s = %s AND m.old_model = %s AND x.%s = m.old_id
                    """,
                    SQL.identifier(table),
                    SQL.identifier(model_column),
                    TEAM_MODEL,
                    SQL.identifier(id_column),
                    SQL.identifier(MAP_TABLE),
                    SQL.identifier(model_column),
                    old_model,
                    old_model,
                    SQL.identifier(id_column),
                )
            )
    for table, column in MODEL_NAME_COLUMNS:
        if table_exists(cr, table) and column_exists(cr, table, column):
            cr.execute(
                SQL(
                    "UPDATE %s SET %s = %s WHERE %s = %s",
                    SQL.identifier(table),
                    SQL.identifier(column),
                    TEAM_MODEL,
                    SQL.identifier(column),
                    old_model,
                )
            )
    cr.execute(
        SQL(
            """
            UPDATE mail_alias a
               SET alias_parent_model_id = (SELECT id FROM ir_model WHERE model = %s),
                   alias_parent_thread_id = m.new_id
              FROM %s m
             WHERE a.alias_parent_model_id = (SELECT id FROM ir_model WHERE model = %s)
               AND m.old_model = %s AND a.alias_parent_thread_id = m.old_id
            """,
            TEAM_MODEL,
            SQL.identifier(MAP_TABLE),
            old_model,
            old_model,
        )
    )


def _repoint_tracking(cr, old_model):
    for column in ("old_value_integer", "new_value_integer"):
        cr.execute(
            SQL(
                """
                UPDATE mail_tracking_value v SET %s = -m.new_id
                  FROM ir_model_fields f, %s m
                 WHERE v.field_id = f.id AND f.relation = %s AND f.ttype = 'many2one'
                   AND m.old_model = %s AND v.%s = m.old_id
                """,
                SQL.identifier(column),
                SQL.identifier(MAP_TABLE),
                old_model,
                old_model,
                SQL.identifier(column),
            )
        )
        cr.execute(
            SQL(
                "UPDATE mail_tracking_value SET %s = -%s WHERE %s < 0",
                SQL.identifier(column),
                SQL.identifier(column),
                SQL.identifier(column),
            )
        )


def _rewrite_expressions(cr, old_model, renamed, links):
    rewrite_quoted_model_names(cr, old_model, TEAM_MODEL)
    for old, new in renamed.items():
        if new is None or new == old:
            continue
        rename_in_stored_expressions(cr, old, new, model=TEAM_MODEL)
        for link in links:
            rename_in_stored_expressions(cr, f"{link}.{old}", f"{link}.{new}")


def _rename_relation_tables(cr, old_model, old_table):
    old_column, new_column = f"{old_table}_id", f"{TEAM_TABLE}_id"
    cr.execute(
        SQL(
            """
            SELECT DISTINCT model, relation, relation_table
              FROM ir_model_fields
             WHERE ttype = 'many2many' AND relation_table IS NOT NULL
               AND (model = %s OR relation = %s)
            """,
            old_model,
            old_model,
        )
    )
    for model, relation, relation_table in cr.fetchall():
        if not table_exists(cr, relation_table):
            continue
        tables = [model.replace(".", "_"), relation.replace(".", "_")]
        target = relation_table
        if relation_table == "_".join(sorted(tables)) + "_rel":
            moved = [TEAM_TABLE if table == old_table else table for table in tables]
            target = "_".join(sorted(moved)) + "_rel"
        if column_exists(cr, relation_table, old_column) and not column_exists(
            cr, relation_table, new_column
        ):
            cr.execute(
                SQL(
                    "ALTER TABLE %s RENAME COLUMN %s TO %s",
                    SQL.identifier(relation_table),
                    SQL.identifier(old_column),
                    SQL.identifier(new_column),
                )
            )
        if target != relation_table and not table_exists(cr, target):
            cr.execute(
                SQL(
                    "ALTER TABLE %s RENAME TO %s",
                    SQL.identifier(relation_table),
                    SQL.identifier(target),
                )
            )
        cr.execute(
            SQL(
                """
                UPDATE ir_model_fields
                   SET relation_table = %s,
                       column1 = CASE WHEN column1 = %s THEN %s ELSE column1 END,
                       column2 = CASE WHEN column2 = %s THEN %s ELSE column2 END
                 WHERE ttype = 'many2many' AND relation_table = %s
                """,
                target,
                old_column,
                new_column,
                old_column,
                new_column,
                relation_table,
            )
        )


def _repoint_model_ids(cr, old_model):
    structural = {
        "ir_model_fields",
        "ir_model_constraint",
        "ir_model_relation",
        "ir_model_inherit",
        "ir_model_access",
        "ir_rule",
    }
    cr.execute(
        """
        SELECT c.conrelid::regclass::text, a.attname
          FROM pg_constraint c
          JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
         WHERE c.contype = 'f' AND c.confrelid = 'ir_model'::regclass
        """
    )
    for table, column in cr.fetchall():
        if table.strip('"') in structural:
            continue
        cr.execute(
            SQL(
                """
                UPDATE %s SET %s = (SELECT id FROM ir_model WHERE model = %s)
                 WHERE %s = (SELECT id FROM ir_model WHERE model = %s)
                """,
                SQL(table),
                SQL.identifier(column),
                TEAM_MODEL,
                SQL.identifier(column),
                old_model,
            )
        )


def _fold_members(cr, old_model, old_table, relation_table, user_column, team_column):
    if not table_exists(cr, relation_table):
        return
    # team.member refuses a live membership of an archived user or team
    team_active = (
        SQL("AND o.active") if column_exists(cr, old_table, "active") else SQL()
    )
    cr.execute(
        SQL(
            """
            INSERT INTO team_member (team_id, user_id, active,
                                     create_uid, create_date, write_uid, write_date)
            SELECT DISTINCT m.new_id, r.%s, true, 1, now() AT TIME ZONE 'UTC',
                   1, now() AT TIME ZONE 'UTC'
              FROM %s r
              JOIN %s m ON m.old_model = %s AND m.old_id = r.%s
              JOIN %s o ON o.id = r.%s
              JOIN res_users u ON u.id = r.%s AND u.active
             WHERE NOT EXISTS (SELECT 1 FROM team_member tm
                                WHERE tm.team_id = m.new_id AND tm.user_id = r.%s
                                  AND tm.active)
               %s
            """,
            SQL.identifier(user_column),
            SQL.identifier(relation_table),
            SQL.identifier(MAP_TABLE),
            old_model,
            SQL.identifier(team_column),
            SQL.identifier(old_table),
            SQL.identifier(team_column),
            SQL.identifier(user_column),
            SQL.identifier(user_column),
            team_active,
        )
    )
    cr.execute(SQL("DELETE FROM ir_model_relation WHERE name = %s", relation_table))
    cr.execute(SQL("DROP TABLE %s", SQL.identifier(relation_table)))


def _move_registry_rows(cr, old_model, old_table, renamed):
    cr.execute(SQL("SELECT id FROM ir_model WHERE model = %s", TEAM_MODEL))
    team_model_id = cr.fetchone()[0]
    cr.execute(SQL("SELECT name, id FROM ir_model_fields WHERE model = %s", TEAM_MODEL))
    team_fields = dict(cr.fetchall())
    cr.execute(SQL("SELECT id, name FROM ir_model_fields WHERE model = %s", old_model))
    for field_id, name in cr.fetchall():
        target = renamed.get(name, name)
        if target is None or target in team_fields:
            if target in team_fields:
                cr.execute(
                    SQL(
                        "UPDATE mail_tracking_value SET field_id = %s WHERE field_id = %s",
                        team_fields[target],
                        field_id,
                    )
                )
            cr.execute(
                SQL(
                    "DELETE FROM ir_model_data WHERE model = 'ir.model.fields' AND res_id = %s",
                    field_id,
                )
            )
            cr.execute(SQL("DELETE FROM ir_model_fields WHERE id = %s", field_id))
            continue
        cr.execute(
            SQL(
                "UPDATE ir_model_fields SET model = %s, model_id = %s, name = %s WHERE id = %s",
                TEAM_MODEL,
                team_model_id,
                target,
                field_id,
            )
        )
        cr.execute(
            SQL(
                """
                UPDATE ir_model_data SET name = %s
                 WHERE model = 'ir.model.fields' AND res_id = %s
                   AND NOT EXISTS (SELECT 1 FROM ir_model_data d2
                                    WHERE d2.module = ir_model_data.module AND d2.name = %s)
                """,
                f"field_{TEAM_TABLE}__{target}",
                field_id,
                f"field_{TEAM_TABLE}__{target}",
            )
        )
        team_fields[target] = field_id
    cr.execute(SQL("SELECT id FROM ir_model WHERE model = %s", old_model))
    row = cr.fetchone()
    if not row:
        return
    old_model_id = row[0]
    for table in ("ir_rule", "ir_model_access"):
        cr.execute(
            SQL(
                """
                DELETE FROM ir_model_data d USING %s r
                 WHERE d.res_id = r.id AND d.model = %s AND r.model_id = %s
                """,
                SQL.identifier(table),
                table.replace("_", ".", 1).replace("model_access", "model.access"),
                old_model_id,
            )
        )
        cr.execute(
            SQL(
                "DELETE FROM %s WHERE model_id = %s",
                SQL.identifier(table),
                old_model_id,
            )
        )
    cr.execute(
        SQL(
            "DELETE FROM ir_model_data WHERE model = 'ir.model' AND res_id = %s",
            old_model_id,
        )
    )
    cr.execute(SQL("DELETE FROM ir_model WHERE id = %s", old_model_id))
