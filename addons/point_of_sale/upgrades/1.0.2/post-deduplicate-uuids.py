import uuid


from odoo.upgrade import util

BUCKET_SIZE = 100000


def migrate(cr, version):
    """
    When UUIDs were introduced for POS [order, order.line, payment] records,
    they were initially generated on the backend, defined as the default value
    on the column. The issue with this is that during the upgrade to 18.0+
    from a version < 18.0, this default value is determined once for the column
    and then applied to all records, resulting in one UUID, duplicated across 
    all existing POS records.
    
    This migration fixes the issue by generating a new UUID for each record
    that has the same UUID as another record. Specifically, it does this for
    the following tables:
    - pos_order
    - pos_order_line
    - pos_payment
    """
    def deduplicate_uuids(table):
        query = f"""
        SELECT UNNEST(ARRAY_AGG(id))
          FROM {table}
         GROUP BY uuid
        HAVING COUNT(*) > 1
        """

        cr.execute(query)
        ids_to_uuids_as_str = ', '.join([
            f"({r[0]}, '{uuid.uuid4()!s}')"
            for r in cr.fetchall()
        ])
        util.explode_execute(
            cr,
            f"""
            WITH vals AS (
              VALUES {ids_to_uuids_as_str}
            )
            UPDATE {table} line
              SET uuid = v.uuid
              FROM vals
                AS v(id, uuid)
            WHERE line.id = v.id
            """,
            table,
            alias="line",
            bucket_size=BUCKET_SIZE
        )

    deduplicate_uuids("pos_order")
    deduplicate_uuids("pos_order_line")
    deduplicate_uuids("pos_payment")
