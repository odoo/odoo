import uuid
from psycopg2.extras import Json

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
        cr.execute(
            f"""
                SELECT UNNEST(ARRAY_AGG(id))
                  FROM {table}
              GROUP BY uuid
                HAVING COUNT(*) > 1
            """
        )

        all_ids = [r[0] for r in cr.fetchall()]
        for ids in cr.split_for_in_conditions(all_ids):
            cr.execute(
                f"UPDATE {table} SET uuid = (%s::json)->>(id::text) WHERE id IN %s",
                [Json({id_: str(uuid.uuid4()) for id_ in ids}), ids]
            )

    deduplicate_uuids("pos_order")
    deduplicate_uuids("pos_order_line")
    deduplicate_uuids("pos_payment")
