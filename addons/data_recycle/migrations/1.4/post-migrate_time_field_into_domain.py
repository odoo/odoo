"""Fold the `time_field_*` triple into the rule's own filter.

An age condition is expressible in the domain itself -- Odoo 19 resolves a
relative value such as ``'today -1y'`` natively -- so the three fields that used
to carry it are gone in 1.4. This is the last stage that can read them: the ORM
drops the columns from ``ir.model.data._process_end``, which runs after every
post-migrate.

The rewrite is exact for a ``datetime`` field. For a ``date`` field the old code
compared against ``fields.Date.today()``, which is UTC, and ``today`` resolves in
the reading user's timezone -- so a rule run by hand by a user east of UTC can
shift its cutoff by up to a day. The cron has no timezone and is unaffected.
"""

import ast
import logging

_logger = logging.getLogger(__name__)

# `relativedelta` keyword -> the suffix Odoo's relative-date values use.
UNIT_SUFFIXES = {"days": "d", "weeks": "w", "months": "m", "years": "y"}


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        SELECT m.id, m.name, m.domain, f.name, f.ttype, m.time_field_delta, m.time_field_delta_unit
          FROM data_recycle_model m
          JOIN ir_model_fields f ON f.id = m.time_field_id
         WHERE m.time_field_id IS NOT NULL
    """)
    rows = cr.fetchall()
    if not rows:
        return

    for rule_id, rule_name, domain, field_name, ttype, delta, unit in rows:
        suffix = UNIT_SUFFIXES.get(unit)
        if not suffix or not delta or delta <= 0:
            # The condition never applied: `_recycle_records` skipped the whole
            # time branch unless all three were truthy, so such a rule selected
            # on its filter alone and still does. Say so -- if the filter is
            # empty the rule now selects everything and 1.4 refuses to run it.
            _logger.warning(
                "data_recycle 1.4: rule %r (id=%s) had a time field but delta=%r unit=%r, "
                "which never filtered anything; its filter is left as it is.",
                rule_name,
                rule_id,
                delta,
                unit,
            )
            continue

        try:
            conditions = list(ast.literal_eval(domain) if domain else [])
        except ValueError, SyntaxError:
            _logger.warning(
                "data_recycle 1.4: rule %r (id=%s) has an unparseable filter %r; "
                "its age condition could not be folded in and is lost.",
                rule_name,
                rule_id,
                domain,
            )
            continue

        # A trailing condition is ANDed with everything before it, whatever
        # operators that part uses, so appending is safe for any domain.
        base = "today" if ttype == "date" else "now"
        conditions.append((field_name, "<=", f"{base} -{delta:d}{suffix}"))
        cr.execute(
            "UPDATE data_recycle_model SET domain = %s WHERE id = %s",
            (repr(conditions), rule_id),
        )
        _logger.info(
            "data_recycle 1.4: rule %r (id=%s) age condition folded into its filter: %r",
            rule_name,
            rule_id,
            conditions,
        )

    _logger.info("data_recycle 1.4: %d rule(s) examined", len(rows))
