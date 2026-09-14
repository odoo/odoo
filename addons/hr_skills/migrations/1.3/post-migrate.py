import logging
from collections import defaultdict
from pathlib import Path

from lxml import etree

from odoo import SUPERUSER_ID, api
from odoo.tools import SQL
from odoo.tools.mail import normalize_url

_logger = logging.getLogger(__name__)

RULES_REWRITTEN = (
    "hr_skill_rule_hr_user",
    "hr_employee_skill_report_manager",
    "hr_employee_skill_history_report_manager",
    "hr_employee_certification_report_manager",
)

SECURITY = Path(__file__).resolve().parents[2] / "security" / "hr_skills_security.xml"


def _rewrite_rules(env):
    tree = etree.parse(str(SECURITY))
    for xmlid in RULES_REWRITTEN:
        rule = env.ref(f"hr_skills.{xmlid}", raise_if_not_found=False)
        if not rule:
            continue
        rule.write(
            {
                field.get("name"): field.text
                for field in tree.find(f".//record[@id='{xmlid}']").iter("field")
                if field.get("name") in ("name", "domain_force")
            }
        )


def _normalize_resume_urls(cr):
    cr.execute(
        """
        SELECT id, external_url
          FROM hr_resume_line
         WHERE external_url IS NOT NULL AND external_url != ''
        """
    )
    changed = [
        (normalized, line_id)
        for line_id, url in cr.fetchall()
        if (normalized := normalize_url(url.strip())) != url
    ]
    for url, line_id in changed:
        cr.execute(
            "UPDATE hr_resume_line SET external_url = %s WHERE id = %s", (url, line_id)
        )
    if changed:
        _logger.warning(
            "hr_skills 1.3: normalized the external URL of resume lines %s",
            sorted(line_id for _url, line_id in changed),
        )
    return [line_id for _url, line_id in changed]


def _overlapping_rows(cr, model):
    linked = SQL.identifier(model._linked_field_name())
    cr.execute(
        SQL(
            """
            SELECT id, valid_from, next_from
              FROM (
                    SELECT s.id, s.valid_from, s.valid_to,
                           lead(s.valid_from) OVER (
                               PARTITION BY s.%(linked)s, s.skill_id
                               ORDER BY s.valid_from, s.id
                           ) AS next_from
                      FROM %(table)s s
                      JOIN hr_skill skill ON skill.id = s.skill_id
                      JOIN hr_skill_type skill_type ON skill_type.id = skill.skill_type_id
                     WHERE NOT (%(certifications_may_overlap)s AND skill_type.is_certification IS TRUE)
                   ) ordered
             WHERE next_from IS NOT NULL
               AND (valid_to IS NULL OR valid_to >= next_from)
            """,
            linked=linked,
            table=SQL.identifier(model._table),
            certifications_may_overlap=model._can_edit_certification_validity_period(),
        )
    )
    return cr.fetchall()


def _repair_overlapping_rows(env):
    repaired = {}
    for model in env["mixin.hr.individual.skill"]._concrete_individual_skill_models():
        rows = _overlapping_rows(env.cr, model)
        clipped = [
            row_id for row_id, valid_from, next_from in rows if next_from > valid_from
        ]
        removed = [
            row_id for row_id, valid_from, next_from in rows if next_from <= valid_from
        ]
        env.cr.execute(
            SQL(
                """
                UPDATE %(table)s s
                   SET valid_to = ordered.next_from - 1
                  FROM (
                        SELECT id,
                               lead(valid_from) OVER (
                                   PARTITION BY %(linked)s, skill_id
                                   ORDER BY valid_from, id
                               ) AS next_from
                          FROM %(table)s
                       ) ordered
                 WHERE s.id = ordered.id AND s.id = ANY(%(ids)s)
                """,
                table=SQL.identifier(model._table),
                linked=SQL.identifier(model._linked_field_name()),
                ids=clipped,
            )
        )
        env.cr.execute(
            SQL(
                "DELETE FROM %(table)s WHERE id = ANY(%(ids)s)",
                table=SQL.identifier(model._table),
                ids=removed,
            )
        )
        if clipped or removed:
            _logger.warning(
                "hr_skills 1.3: %s rows overlapped a later row of the same skill; "
                "ended %s the day before their successor, deleted %s that started "
                "on the same day",
                model._name,
                sorted(clipped),
                sorted(removed),
            )
            repaired[model._name] = (sorted(clipped), sorted(removed))
    env.invalidate_all()
    return repaired


def _link_certification_reminders(env):
    activity_type = env.ref(
        "hr_skills.mail_activity_data_upload_certification", raise_if_not_found=False
    )
    if not activity_type:
        return {}
    activities = (
        env["mail.activity"]
        .with_context(active_test=False)
        .search(
            [
                ("activity_type_id", "=", activity_type.id),
                ("res_model", "=", "hr.employee"),
                ("certification_skill_id", "=", False),
            ]
        )
    )
    if not activities:
        return {}
    levels = env["hr.skill.level"].search(
        [("skill_type_id.is_certification", "=", True)]
    )
    requirement_by_summary = {}
    for lang in {"en_US", *env.registry.locale.installed_langs(env)}:
        for level in levels.with_context(lang=lang):
            for skill in level.skill_type_id.skill_ids.with_context(lang=lang):
                requirement_by_summary.setdefault(
                    f"{skill.name}: {level.name}", (skill.id, level.id)
                )
    linked = defaultdict(lambda: env["mail.activity"])
    for activity in activities:
        if requirement := requirement_by_summary.get(activity.summary):
            linked[requirement] |= activity
    for (skill_id, level_id), matched in linked.items():
        matched.write(
            {
                "certification_skill_id": skill_id,
                "certification_skill_level_id": level_id,
            }
        )
    unmatched = activities - env["mail.activity"].union(*linked.values())
    _logger.warning(
        "hr_skills 1.3: linked %s certification reminders to their requirement, "
        "left %s unmatched: %s",
        len(activities) - len(unmatched),
        len(unmatched),
        unmatched.ids,
    )
    return linked


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    _rewrite_rules(env)
    _normalize_resume_urls(cr)
    _repair_overlapping_rows(env)
    _link_certification_reminders(env)
