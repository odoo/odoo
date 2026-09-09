import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'slide_question'
        )
    """)
    if not cr.fetchone()[0]:
        _logger.info("No slide_question table found — skipping quiz migration")
        return

    cr.execute("SELECT COUNT(*) FROM slide_question")
    question_count = cr.fetchone()[0]
    if not question_count:
        _logger.info("No slide_question rows — skipping quiz migration")
        return

    _logger.info(
        "Migrating %d slide.question records to survey.question", question_count
    )

    cr.execute(
        "ALTER TABLE survey_survey ADD COLUMN IF NOT EXISTS _marin_from_slide_id INTEGER"
    )
    cr.execute(
        "ALTER TABLE survey_question ADD COLUMN IF NOT EXISTS _marin_from_slide_question_id INTEGER"
    )
    cr.execute(
        "ALTER TABLE survey_question_answer ADD COLUMN IF NOT EXISTS _marin_from_slide_answer_id INTEGER"
    )

    cr.execute("""
        INSERT INTO survey_survey (
            title, survey_type, access_token, scoring_type, scoring_success_min,
            questions_layout, questions_selection, access_mode,
            certification, active, _marin_from_slide_id,
            create_uid, create_date, write_uid, write_date
        )
        SELECT DISTINCT ON (ss.id)
            ss.name,
            'custom',
            gen_random_uuid()::text,
            'scoring_without_answers',
            100.0,
            'one_page',
            'all',
            -- A channel restricted to its enrolled attendees ('members')
            -- should not give its quiz survey a public/link-only access
            -- mode; every other visibility (public/connected/link) maps to
            -- the survey's own "public" (i.e. "anyone with the link").
            CASE WHEN sc.visibility = 'members' THEN 'token' ELSE 'public' END,
            false,
            true,
            ss.id,
            ss.create_uid, NOW(), ss.write_uid, NOW()
        FROM slide_slide ss
        JOIN slide_question sq ON sq.slide_id = ss.id
        LEFT JOIN slide_channel sc ON sc.id = ss.channel_id
        WHERE ss.survey_id IS NULL
    """)
    surveys_created = cr.rowcount
    _logger.info("Created %d survey.survey records for quiz slides", surveys_created)

    cr.execute("""
        UPDATE slide_slide ss
        SET survey_id = sv.id
        FROM survey_survey sv
        WHERE sv._marin_from_slide_id = ss.id
          AND ss.survey_id IS NULL
    """)

    cr.execute("""
        INSERT INTO survey_question (
            survey_id, title, sequence, question_type, is_page,
            _marin_from_slide_question_id,
            create_uid, create_date, write_uid, write_date
        )
        SELECT
            ss.survey_id, sq.question, sq.sequence, 'simple_choice', false,
            sq.id,
            sq.create_uid, sq.create_date, sq.write_uid, sq.write_date
        FROM slide_question sq
        JOIN slide_slide ss ON sq.slide_id = ss.id
        JOIN survey_survey sv ON ss.survey_id = sv.id
        WHERE sv._marin_from_slide_id IS NOT NULL
    """)
    questions_migrated = cr.rowcount
    _logger.info("Migrated %d slide_question → survey_question", questions_migrated)

    cr.execute("""
        INSERT INTO survey_question_answer (
            question_id, value, sequence, is_correct, answer_score, comment,
            _marin_from_slide_answer_id,
            create_uid, create_date, write_uid, write_date
        )
        SELECT
            sq_new.id, sa.text_value, sa.sequence, sa.is_correct,
            CASE WHEN sa.is_correct THEN 1.0 ELSE 0.0 END,
            sa.comment,
            sa.id,
            sa.create_uid, sa.create_date, sa.write_uid, sa.write_date
        FROM slide_answer sa
        JOIN slide_question sq_old ON sa.question_id = sq_old.id
        JOIN survey_question sq_new ON sq_new._marin_from_slide_question_id = sq_old.id
    """)
    answers_migrated = cr.rowcount
    _logger.info("Migrated %d slide_answer → survey_question_answer", answers_migrated)

    cr.execute("""
        UPDATE ir_model_data imd
        SET model = 'survey.question', res_id = sq.id
        FROM survey_question sq
        WHERE imd.model = 'slide.question'
          AND sq._marin_from_slide_question_id = imd.res_id
    """)
    cr.execute("""
        UPDATE ir_model_data imd
        SET model = 'survey.question.answer', res_id = sqa.id
        FROM survey_question_answer sqa
        WHERE imd.model = 'slide.answer'
          AND sqa._marin_from_slide_answer_id = imd.res_id
    """)

    # Guard: step 3 only migrates questions for slides whose survey THIS
    # migration created (`sv._marin_from_slide_id IS NOT NULL`) -- a slide
    # that already had its own survey_id before this ran (e.g. a
    # certification slide with pre-existing questions) is skipped there, so
    # its slide_question rows are never copied. The cleanup below would
    # orphan them (their model registration disappears even though the
    # rows themselves are never dropped). Abort loudly rather than silently
    # losing that content.
    cr.execute("""
        SELECT COUNT(*)
        FROM slide_question sq
        JOIN slide_slide ss ON sq.slide_id = ss.id
        LEFT JOIN survey_survey sv
            ON ss.survey_id = sv.id AND sv._marin_from_slide_id IS NOT NULL
        WHERE sv.id IS NULL
    """)
    orphaned_question_count = cr.fetchone()[0]
    if orphaned_question_count:
        raise RuntimeError(
            f"Quiz migration would orphan {orphaned_question_count} "
            "slide_question row(s) belonging to a slide that already had "
            "its own survey_id before this migration ran. Migrate those "
            "rows into their existing survey manually before re-running."
        )

    # Clean up remaining XML IDs that weren't remapped
    cr.execute(
        "DELETE FROM ir_model_data WHERE model IN ('slide.question', 'slide.answer')"
    )

    cr.execute("DELETE FROM ir_model WHERE model IN ('slide.question', 'slide.answer')")
    cr.execute(
        "DELETE FROM ir_model_fields WHERE model IN ('slide.question', 'slide.answer')"
    )
    cr.execute(
        "UPDATE ir_model_fields SET relation = 'survey.question' WHERE relation = 'slide.question'"
    )
    cr.execute(
        "UPDATE ir_model_fields SET relation = 'survey.question.answer' WHERE relation = 'slide.answer'"
    )

    cr.execute("ALTER TABLE survey_survey DROP COLUMN IF EXISTS _marin_from_slide_id")
    cr.execute(
        "ALTER TABLE survey_question DROP COLUMN IF EXISTS _marin_from_slide_question_id"
    )
    cr.execute(
        "ALTER TABLE survey_question_answer DROP COLUMN IF EXISTS _marin_from_slide_answer_id"
    )

    cr.execute(
        "SELECT setval('survey_survey_id_seq', COALESCE(MAX(id), 1), true) FROM survey_survey"
    )
    cr.execute(
        "SELECT setval('survey_question_id_seq', COALESCE(MAX(id), 1), true) FROM survey_question"
    )
    cr.execute(
        "SELECT setval('survey_question_answer_id_seq', COALESCE(MAX(id), 1), true) FROM survey_question_answer"
    )

    _logger.info(
        "Quiz migration complete: %d surveys, %d questions, %d answers",
        surveys_created,
        questions_migrated,
        answers_migrated,
    )
