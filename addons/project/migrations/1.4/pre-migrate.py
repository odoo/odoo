import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version: str | None) -> None:
    if not version:
        return

    _logger.info("project v1.4 pre-migrate: PMI terminology alignment starting")

    _create_workflow_step_table(cr)
    _create_workflow_step_project_rel(cr)
    _create_triage_table(cr)
    _create_task_triage_table(cr)

    _rename_project_stage_to_phase(cr)
    _rename_task_dependency_rel(cr)

    _rename_project_task_columns(cr)
    _rename_project_project_columns(cr)

    _migrate_state_values(cr)

    _update_ir_model(cr)
    _update_ir_model_data(cr)
    _update_ir_model_fields(cr)

    _update_ir_filters(cr)
    _update_access_domains(cr)
    _update_server_actions(cr)

    _drop_orphaned_stage_id_from_user_rel(cr)
    _update_foreign_keys(cr)
    _drop_orphaned_wizard_rel(cr)

    _logger.info("project v1.4 pre-migrate: PMI terminology alignment complete")


def _create_workflow_step_table(cr) -> None:
    cr.execute("""
        CREATE TABLE IF NOT EXISTS project_workflow_step (
            id                      SERIAL PRIMARY KEY,
            active                  BOOLEAN DEFAULT TRUE,
            name                    JSONB NOT NULL,
            sequence                INTEGER DEFAULT 1,
            color                   INTEGER,
            fold                    BOOLEAN DEFAULT FALSE,
            auto_update_state       BOOLEAN DEFAULT FALSE,
            mail_template_id        INTEGER,
            rating_template_id      INTEGER,
            rotting_threshold_days  INTEGER DEFAULT 0,
            rating_active           BOOLEAN DEFAULT FALSE,
            rating_status           VARCHAR DEFAULT 'stage',
            rating_status_period    VARCHAR DEFAULT 'monthly',
            rating_request_deadline TIMESTAMP WITHOUT TIME ZONE,
            create_date             TIMESTAMP WITHOUT TIME ZONE,
            create_uid              INTEGER,
            write_date              TIMESTAMP WITHOUT TIME ZONE,
            write_uid               INTEGER
        )
    """)

    cr.execute("""
        INSERT INTO project_workflow_step (
            id, active, name, sequence, color, fold,
            auto_update_state,
            mail_template_id, rating_template_id, rotting_threshold_days,
            rating_active, rating_status, rating_status_period,
            rating_request_deadline,
            create_date, create_uid, write_date, write_uid
        )
        SELECT
            id, active, name, sequence, color, fold,
            auto_validation_state,
            mail_template_id, rating_template_id, rotting_threshold_days,
            rating_active, rating_status, rating_status_period,
            rating_request_deadline,
            create_date, create_uid, write_date, write_uid
        FROM project_task_type
        WHERE user_id IS NULL
        ON CONFLICT (id) DO NOTHING
    """)
    inserted = cr.rowcount
    _logger.info("project_workflow_step: inserted %d rows", inserted)

    cr.execute("""
        SELECT setval(
            'project_workflow_step_id_seq',
            COALESCE((SELECT MAX(id) FROM project_workflow_step), 1),
            true
        )
    """)


def _create_workflow_step_project_rel(cr) -> None:
    cr.execute("""
        CREATE TABLE IF NOT EXISTS project_workflow_step_project_rel (
            step_id    INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            PRIMARY KEY (step_id, project_id)
        )
    """)

    cr.execute("""
        INSERT INTO project_workflow_step_project_rel (step_id, project_id)
        SELECT r.type_id, r.project_id
        FROM   project_task_type_rel r
        JOIN   project_task_type     t ON t.id = r.type_id
        WHERE  t.user_id IS NULL
        ON CONFLICT DO NOTHING
    """)
    _logger.info("project_workflow_step_project_rel: inserted %d rows", cr.rowcount)


def _create_triage_table(cr) -> None:
    cr.execute("""
        CREATE TABLE IF NOT EXISTS project_triage (
            id          SERIAL PRIMARY KEY,
            active      BOOLEAN DEFAULT TRUE,
            name        JSONB NOT NULL,
            sequence    INTEGER DEFAULT 1,
            color       INTEGER DEFAULT 0,
            fold        BOOLEAN DEFAULT FALSE,
            user_id     INTEGER,
            create_date TIMESTAMP WITHOUT TIME ZONE,
            create_uid  INTEGER,
            write_date  TIMESTAMP WITHOUT TIME ZONE,
            write_uid   INTEGER
        )
    """)

    cr.execute("""
        INSERT INTO project_triage (
            id, active, name, sequence, color, fold, user_id,
            create_date, create_uid, write_date, write_uid
        )
        SELECT
            id, active, name, sequence, COALESCE(color, 0), fold, user_id,
            create_date, create_uid, write_date, write_uid
        FROM project_task_type
        WHERE user_id IS NOT NULL
        ON CONFLICT (id) DO NOTHING
    """)
    inserted = cr.rowcount
    _logger.info("project_triage: inserted %d rows", inserted)

    cr.execute("""
        SELECT setval(
            'project_triage_id_seq',
            COALESCE((SELECT MAX(id) FROM project_triage), 1),
            true
        )
    """)


def _create_task_triage_table(cr) -> None:
    cr.execute("""
        CREATE TABLE IF NOT EXISTS project_task_triage (
            id          SERIAL PRIMARY KEY,
            task_id     INTEGER NOT NULL,
            user_id     INTEGER NOT NULL,
            triage_id   INTEGER,
            create_date TIMESTAMP WITHOUT TIME ZONE,
            create_uid  INTEGER,
            write_date  TIMESTAMP WITHOUT TIME ZONE,
            write_uid   INTEGER,
            CONSTRAINT project_task_triage__project_task_triage_unique
                UNIQUE (task_id, user_id)
        )
    """)

    cr.execute("""
        INSERT INTO project_task_triage (
            id, task_id, user_id, triage_id,
            create_date, create_uid, write_date, write_uid
        )
        SELECT
            id, task_id, user_id, stage_id,
            create_date, create_uid, write_date, write_uid
        FROM project_task_user_rel
        ON CONFLICT (id) DO NOTHING
    """)
    inserted = cr.rowcount
    _logger.info("project_task_triage: inserted %d rows", inserted)

    cr.execute("""
        SELECT setval(
            'project_task_triage_id_seq',
            COALESCE((SELECT MAX(id) FROM project_task_triage), 1),
            true
        )
    """)


def _rename_project_stage_to_phase(cr) -> None:
    cr.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'project_project_stage'
    """)
    if cr.fetchone():
        cr.execute("ALTER TABLE project_project_stage RENAME TO project_phase")
        _logger.info("Renamed table: project_project_stage → project_phase")

        cr.execute("""
            DO $$
            BEGIN
                ALTER SEQUENCE IF EXISTS project_project_stage_id_seq
                    RENAME TO project_phase_id_seq;
            EXCEPTION WHEN undefined_table THEN
                NULL;
            END $$;
        """)
    else:
        _logger.info(
            "Table project_project_stage not found (already renamed or fresh install)"
        )


def _rename_task_dependency_rel(cr) -> None:
    cr.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'task_dependencies_rel'
    """)
    if cr.fetchone():
        cr.execute(
            "ALTER TABLE task_dependencies_rel RENAME TO project_task_dependency_rel"
        )
        _logger.info(
            "Renamed table: task_dependencies_rel → project_task_dependency_rel"
        )
    else:
        _logger.info(
            "Table task_dependencies_rel not found (already renamed or fresh install)"
        )


def _column_exists(cr, table: str, column: str) -> bool:
    cr.execute(
        """
        SELECT 1
        FROM   information_schema.columns
        WHERE  table_name  = %s
          AND  column_name = %s
    """,
        (table, column),
    )
    return bool(cr.fetchone())


def _rename_project_task_columns(cr) -> None:
    if _column_exists(cr, "project_task", "stage_id"):
        cr.execute("ALTER TABLE project_task RENAME COLUMN stage_id TO step_id")
        _logger.info("Renamed column: project_task.stage_id → step_id")
    elif _column_exists(cr, "project_task", "step_id"):
        _logger.info("project_task.step_id already exists, skipping rename")
    else:
        _logger.warning("project_task: neither stage_id nor step_id found")

    if _column_exists(cr, "project_task", "date_last_stage_update"):
        cr.execute(
            "ALTER TABLE project_task RENAME COLUMN date_last_stage_update TO date_last_status_change"
        )
        _logger.info(
            "Renamed column: project_task.date_last_stage_update → date_last_status_change"
        )
    elif _column_exists(cr, "project_task", "date_last_status_change"):
        _logger.info(
            "project_task.date_last_status_change already exists, skipping rename"
        )


def _rename_project_project_columns(cr) -> None:
    if _column_exists(cr, "project_project", "stage_id"):
        cr.execute("ALTER TABLE project_project RENAME COLUMN stage_id TO phase_id")
        _logger.info("Renamed column: project_project.stage_id → phase_id")
    elif _column_exists(cr, "project_project", "phase_id"):
        _logger.info("project_project.phase_id already exists, skipping rename")
    else:
        _logger.warning("project_project: neither stage_id nor phase_id found")

    if _column_exists(cr, "project_project", "allow_task_dependencies"):
        cr.execute(
            "ALTER TABLE project_project RENAME COLUMN allow_task_dependencies TO allow_dependencies"
        )
        _logger.info(
            "Renamed column: project_project.allow_task_dependencies → allow_dependencies"
        )
    elif _column_exists(cr, "project_project", "allow_dependencies"):
        _logger.info(
            "project_project.allow_dependencies already exists, skipping rename"
        )


_STATE_MAP = {
    "00_todo": "todo",
    "01_in_progress": "in_progress",
    "02_changes_requested": "changes_requested",
    "03_approved": "approved",
    "04_waiting_normal": "blocked",
    "1_done": "done",
    "1_canceled": "canceled",
}


def _migrate_state_values(cr) -> None:
    old_values = list(_STATE_MAP.keys())
    cr.execute(
        """
        SELECT state, COUNT(*)
        FROM   project_task
        WHERE  state = ANY(%s)
        GROUP  BY state
    """,
        (old_values,),
    )
    counts = dict(cr.fetchall())

    if not counts:
        _logger.info("project_task.state: no legacy values found, skipping")
        return

    for old, new in _STATE_MAP.items():
        if old not in counts:
            continue
        cr.execute(
            "UPDATE project_task SET state = %s WHERE state = %s",
            (new, old),
        )
        _logger.info("project_task.state: %s → %s (%d rows)", old, new, counts[old])


_MODEL_RENAMES = {
    "project.task.type": "project.workflow.step",
    "project.project.stage": "project.phase",
    "project.task.stage.personal": "project.task.triage",
}

_FIELD_RENAMES = {
    ("project.task", "stage_id"): "step_id",
    ("project.task", "date_last_stage_update"): "date_last_status_change",
    ("project.project", "stage_id"): "phase_id",
    ("project.project", "allow_task_dependencies"): "allow_dependencies",
}


def _update_ir_model(cr) -> None:
    for old_name, new_name in _MODEL_RENAMES.items():
        cr.execute(
            "UPDATE ir_model SET model = %s WHERE model = %s",
            (new_name, old_name),
        )
        if cr.rowcount:
            _logger.info("ir_model: %s → %s", old_name, new_name)


def _update_ir_model_data(cr) -> None:
    cr.execute("""
        UPDATE ir_model_data
        SET model = 'project.workflow.step'
        WHERE model = 'project.task.type'
    """)
    step_count = cr.rowcount
    _logger.info(
        "ir_model_data: project.task.type → project.workflow.step (%d rows)", step_count
    )

    cr.execute("""
        UPDATE ir_model_data imd
        SET model = 'project.triage'
        FROM project_triage pt
        WHERE imd.model = 'project.workflow.step'
          AND imd.res_id = pt.id
    """)
    triage_count = cr.rowcount
    _logger.info(
        "ir_model_data: project.workflow.step → project.triage (%d rows, personal stages)",
        triage_count,
    )

    cr.execute("""
        UPDATE ir_model_data
        SET model = 'project.phase'
        WHERE model = 'project.project.stage'
    """)
    _logger.info(
        "ir_model_data: project.project.stage → project.phase (%d rows)", cr.rowcount
    )

    cr.execute("""
        UPDATE ir_model_data
        SET model = 'project.task.triage'
        WHERE model = 'project.task.stage.personal'
    """)
    _logger.info(
        "ir_model_data: project.task.stage.personal → project.task.triage (%d rows)",
        cr.rowcount,
    )


def _update_ir_model_fields(cr) -> None:
    for (model, old_field), new_field in _FIELD_RENAMES.items():
        cr.execute(
            "UPDATE ir_model_fields SET name = %s WHERE model = %s AND name = %s",
            (new_field, model, old_field),
        )
        if cr.rowcount:
            _logger.info("ir_model_fields: %s.%s → %s", model, old_field, new_field)

    for old_model, new_model in _MODEL_RENAMES.items():
        cr.execute(
            "UPDATE ir_model_fields SET model = %s WHERE model = %s",
            (new_model, old_model),
        )
        if cr.rowcount:
            _logger.info(
                "ir_model_fields: updated %d fields for %s → %s",
                cr.rowcount,
                old_model,
                new_model,
            )

    for old_model, new_model in _MODEL_RENAMES.items():
        cr.execute(
            "UPDATE ir_model_fields SET relation = %s WHERE relation = %s",
            (new_model, old_model),
        )
        if cr.rowcount:
            _logger.info(
                "ir_model_fields: updated %d relation refs for %s → %s",
                cr.rowcount,
                old_model,
                new_model,
            )


_FILTER_FIELD_RENAMES = [
    ("project.task", "stage_id", "step_id"),
    ("project.task", "date_last_stage_update", "date_last_status_change"),
    ("project.task", "personal_stage_type_id", "triage_id"),
    ("project.task", "personal_stage_type_ids", "triage_ids"),
    ("project.task", "personal_stage_id", "personal_triage_id"),
    ("project.task", "depend_on_ids", "predecessor_ids"),
    ("project.task", "dependent_ids", "successor_ids"),
    ("project.task", "depend_on_count", "predecessor_count"),
    ("project.task", "closed_depend_on_count", "closed_predecessor_count"),
    ("project.task", "dependent_count", "successor_count"),
    ("project.task", "allow_task_dependencies", "allow_dependencies"),
    ("project.project", "stage_id", "phase_id"),
    ("project.project", "type_ids", "workflow_step_ids"),
]

_FILTER_STATE_RENAMES = [
    ("00_todo", "todo"),
    ("01_in_progress", "in_progress"),
    ("02_changes_requested", "changes_requested"),
    ("03_approved", "approved"),
    ("04_waiting_normal", "blocked"),
    ("1_done", "done"),
    ("1_canceled", "canceled"),
]


def _text_replace(
    cr,
    table: str,
    column: str,
    old: str,
    new: str,
    where_clause: str = "",
    params: tuple[str, ...] = (),
) -> int:
    sql = f"""
        UPDATE {table}
        SET {column} = replace({column}, %s, %s)
        WHERE {column} LIKE %s
    """
    like_pattern = f"%{old}%"
    query_params = [old, new, like_pattern, *params]
    if where_clause:
        sql += f" AND {where_clause}"
    cr.execute(sql, query_params)
    return cr.rowcount


def _update_ir_filters(cr) -> None:
    total = 0

    for old_model, new_model in _MODEL_RENAMES.items():
        cr.execute(
            "UPDATE ir_filters SET model_id = %s WHERE model_id = %s",
            (new_model, old_model),
        )
        if cr.rowcount:
            _logger.info(
                "ir_filters.model_id: %s → %s (%d rows)",
                old_model,
                new_model,
                cr.rowcount,
            )
            total += cr.rowcount

    for model, old_field, new_field in _FILTER_FIELD_RENAMES:
        for column in ("domain", "context", "sort"):
            count = _text_replace(
                cr,
                "ir_filters",
                column,
                old_field,
                new_field,
                where_clause="model_id = %s",
                params=(model,),
            )
            if count:
                _logger.info(
                    "ir_filters.%s: %s → %s on %s (%d rows)",
                    column,
                    old_field,
                    new_field,
                    model,
                    count,
                )
                total += count

    for old_state, new_state in _FILTER_STATE_RENAMES:
        count = _text_replace(
            cr,
            "ir_filters",
            "domain",
            old_state,
            new_state,
            where_clause="model_id = %s",
            params=("project.task",),
        )
        if count:
            _logger.info(
                "ir_filters.domain: state %s → %s (%d rows)",
                old_state,
                new_state,
                count,
            )
            total += count

    _logger.info("ir_filters: %d total updates", total)


def _update_access_domains(cr) -> None:
    total = 0

    for model, old_field, new_field in _FILTER_FIELD_RENAMES:
        cr.execute(
            """
            UPDATE ir_access r
            SET domain = replace(r.domain, %s, %s)
            FROM ir_model m
            WHERE r.model_id = m.id
              AND m.model = %s
              AND r.domain LIKE %s
        """,
            (old_field, new_field, model, f"%{old_field}%"),
        )
        if cr.rowcount:
            _logger.info(
                "ir_access.domain: %s → %s on %s (%d rows)",
                old_field,
                new_field,
                model,
                cr.rowcount,
            )
            total += cr.rowcount

    for old_state, new_state in _FILTER_STATE_RENAMES:
        cr.execute(
            """
            UPDATE ir_access r
            SET domain = replace(r.domain, %s, %s)
            FROM ir_model m
            WHERE r.model_id = m.id
              AND m.model = 'project.task'
              AND r.domain LIKE %s
        """,
            (old_state, new_state, f"%{old_state}%"),
        )
        if cr.rowcount:
            _logger.info(
                "ir_access.domain: state %s → %s (%d rows)",
                old_state,
                new_state,
                cr.rowcount,
            )
            total += cr.rowcount

    _logger.info("ir_access: %d total updates", total)


def _update_server_actions(cr) -> None:
    total = 0

    for model, old_field, new_field in _FILTER_FIELD_RENAMES:
        cr.execute(
            """
            UPDATE ir_act_server a
            SET update_path = replace(a.update_path, %s, %s)
            FROM ir_model m
            WHERE a.model_id = m.id
              AND m.model = %s
              AND a.update_path LIKE %s
        """,
            (old_field, new_field, model, f"%{old_field}%"),
        )
        if cr.rowcount:
            _logger.info(
                "ir_act_server.update_path: %s → %s on %s (%d rows)",
                old_field,
                new_field,
                model,
                cr.rowcount,
            )
            total += cr.rowcount

        cr.execute(
            """
            UPDATE ir_act_server a
            SET code = replace(a.code, %s, %s)
            FROM ir_model m
            WHERE a.model_id = m.id
              AND m.model = %s
              AND a.code LIKE %s
        """,
            (old_field, new_field, model, f"%{old_field}%"),
        )
        if cr.rowcount:
            _logger.info(
                "ir_act_server.code: %s → %s on %s (%d rows)",
                old_field,
                new_field,
                model,
                cr.rowcount,
            )
            total += cr.rowcount

    _logger.info("ir_act_server: %d total updates", total)


def _drop_orphaned_stage_id_from_user_rel(cr) -> None:
    if _column_exists(cr, "project_task_user_rel", "stage_id"):
        cr.execute("ALTER TABLE project_task_user_rel DROP COLUMN stage_id")
        _logger.info("project_task_user_rel: dropped orphaned stage_id column")
    if _column_exists(cr, "project_task_user_rel", "id"):
        cr.execute("""
            DO $$
            BEGIN
                ALTER TABLE project_task_user_rel DROP CONSTRAINT IF EXISTS project_task_user_rel_pkey;
            EXCEPTION WHEN undefined_object THEN
                NULL;
            END $$;
        """)
        cr.execute("ALTER TABLE project_task_user_rel DROP COLUMN id")
        _logger.info("project_task_user_rel: dropped orphaned id column")


def _update_foreign_keys(cr) -> None:
    cr.execute("""
        ALTER TABLE project_task
        DROP CONSTRAINT IF EXISTS project_task_stage_id_fkey
    """)
    cr.execute("""
        DO $$
        BEGIN
            ALTER TABLE project_task
            ADD CONSTRAINT project_task_step_id_fkey
                FOREIGN KEY (step_id) REFERENCES project_workflow_step(id)
                ON DELETE RESTRICT;
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """)
    _logger.info("project_task: FK step_id → project_workflow_step")

    cr.execute("""
        ALTER TABLE project_task_type_rel
        DROP CONSTRAINT IF EXISTS project_task_type_rel_type_id_fkey
    """)
    _logger.info("project_task_type_rel: dropped orphaned FK to project_task_type")


def _drop_orphaned_wizard_rel(cr) -> None:
    cr.execute("""
        DROP TABLE IF EXISTS project_task_type_project_task_type_delete_wizard_rel
    """)
    _logger.info(
        "Dropped orphaned table: project_task_type_project_task_type_delete_wizard_rel"
    )
