import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Collapse duplicate cities before the unique index is (re)built.

    The index is created during _auto_init, which runs before obsolete data
    records are removed at the end of the load. A database that already holds
    duplicates therefore never gets the index: PostgreSQL refuses it, Odoo logs
    the refusal and the upgrade still exits 0. Deduplicating here is what makes
    the constraint take effect on an existing database rather than only on a
    fresh install.
    """
    if not version:
        return

    cr.execute(
        """
        WITH ranked AS (
            SELECT id,
                   first_value(id) OVER (
                       PARTITION BY name ->> 'en_US', zipcode, state_id, country_id
                       ORDER BY id
                   ) AS keeper
              FROM res_city
        )
        SELECT id, keeper FROM ranked WHERE id <> keeper
        """
    )
    duplicates = cr.fetchall()
    if not duplicates:
        return

    cr.execute(
        """
        UPDATE res_partner partner
           SET city_id = mapping.keeper
          FROM unnest(%s::int[], %s::int[]) AS mapping(dup, keeper)
         WHERE partner.city_id = mapping.dup
        """,
        ([dup for dup, _keeper in duplicates], [keeper for _dup, keeper in duplicates]),
    )
    repointed = cr.rowcount

    doomed = [dup for dup, _keeper in duplicates]
    cr.execute(
        "DELETE FROM ir_model_data WHERE model = 'res.city' AND res_id = ANY(%s)",
        (doomed,),
    )
    cr.execute("DELETE FROM res_city WHERE id = ANY(%s)", (doomed,))

    _logger.info(
        "res.city deduplicated for the name/zipcode/state/country index: "
        "%d duplicate cities removed, %d partners repointed to the surviving row.",
        len(doomed),
        repointed,
    )
