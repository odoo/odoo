"""Put stored period domains back into the natural bound order.

Until 19.0.1.1.0 this module shipped its own ``daterange`` domain operator, and
``date.range.get_domain_for_field`` deliberately emitted the mirrored bound order --
``<=`` before ``>=`` -- so that operator could claim a domain shape the web
client's own ``in range`` would otherwise have taken first.

There is no separate operator now. A period is a plain range whose bounds the
value editor recognises by matching them against the known ranges, so it wants
the order core recognises. A domain still stored the other way round filters
exactly the same records -- ``&`` is commutative and nothing about evaluation
changes -- but the editor no longer sees a range in it, and renders the pair as
two unrelated conditions instead of one period.

This rewrites the pairs it can prove are one of ours: two adjacent conditions on
the same date or datetime field, ``<=`` then ``>=``, whose bounds match an
existing date.range exactly. Requiring the match is what makes it safe -- a
hand-written ``<=``/``>=`` pair that happens to sit in that order is left alone,
because it never was a period and turning it round would be a change the author
did not ask for.

Domains live in several tables and in several shapes (a list literal in a
``Char``, one leaf of a bigger nested domain), so this only touches the shapes it
can parse and match, and logs a count of what it converted. Anything it skips
keeps working; it just does not get the period selector back.
"""

import ast
import logging

_logger = logging.getLogger(__name__)

# (table, column) pairs holding a domain as a text literal.
_DOMAIN_COLUMNS = (
    ("ir_filters", "domain"),
    ("ir_access", "domain"),
    ("ir_act_window", "domain"),
    ("ir_act_server", "value"),
)


def migrate(cr, version):
    if not version:
        return

    cr.execute("SELECT id, date_start, date_end FROM date_range")
    known = {(str(start), str(end)) for _id, start, end in cr.fetchall()}
    if not known:
        return

    converted = 0
    for table, column in _DOMAIN_COLUMNS:
        cr.execute(
            """
            SELECT to_regclass(%s) IS NOT NULL
                   AND EXISTS (
                       SELECT 1 FROM information_schema.columns
                       WHERE table_name = %s AND column_name = %s
                   )
            """,
            (table, table, column),
        )
        if not cr.fetchone()[0]:
            continue
        # `<=` before `>=` on the same field is the signature; the LIKE keeps
        # the row set small before anything is parsed.
        cr.execute(
            # A single %s: an f-string does no %-formatting, so doubling it
            # leaves a literal %%s that psycopg sees as zero placeholders.
            f"SELECT id, {column} FROM {table} WHERE {column} LIKE %s",
            ("%<=%",),
        )
        for row_id, domain in cr.fetchall():
            rewritten = _rewrite(domain, known)
            if rewritten is None:
                continue
            cr.execute(
                f"UPDATE {table} SET {column} = %s WHERE id = %s",
                (rewritten, row_id),
            )
            converted += 1

    if converted:
        _logger.info(
            "date_range: reordered the bounds of %d stored period domain(s) so "
            "the domain editor shows them as periods again.",
            converted,
        )


def _rewrite(domain, known):
    """Return the domain with mirrored period pairs turned round, or None.

    None means "nothing to do" — unparseable, or containing no pair that is
    provably one of ours.

    :param str domain: the stored domain text
    :param set known: {(date_start, date_end)} of every existing date.range
    :rtype: str | None
    """
    if not domain or "<=" not in domain:
        return None
    try:
        parsed = ast.literal_eval(domain)
    except ValueError, SyntaxError:
        # Domains may be arbitrary Python evaluated against a context
        # (`[('date', '<=', context_today())]`). Those are not ours to touch.
        return None
    if not isinstance(parsed, list):
        return None

    changed = False
    index = 0
    while index < len(parsed) - 1:
        first, second = parsed[index], parsed[index + 1]
        if _is_mirrored_period(first, second, known):
            parsed[index], parsed[index + 1] = second, first
            changed = True
            index += 2
            continue
        index += 1
    return repr(parsed) if changed else None


def _is_mirrored_period(first, second, known):
    """Whether two adjacent leaves are one of this module's period pairs."""
    for leaf in (first, second):
        if not isinstance(leaf, (list, tuple)) or len(leaf) != 3:
            return False
    field, op1, end = first
    other_field, op2, start = second
    if field != other_field or op1 != "<=" or op2 != ">=":
        return False
    if not isinstance(start, str) or not isinstance(end, str):
        return False
    # A datetime bound carries a time; a period's bounds are whole days, and the
    # date half is what date.range stores.
    return (start[:10], end[:10]) in known
