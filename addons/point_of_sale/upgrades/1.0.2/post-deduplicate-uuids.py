import uuid
from psycopg2.extras import Json
from odoo.tools import split_every

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
         WHERE uuid IS NOT NULL
         GROUP BY uuid
        HAVING COUNT(*) > 1
        """
        while True:
            cr.execute(query)
            if not cr.rowcount:
                break
            ids = tuple(r[0] for r in cr.fetchmany(10000))
            cr.execute(
                f"UPDATE {table} SET uuid = (%s::json)->>(id::text) WHERE id IN %s",
                [Json({id_: str(uuid.uuid4()) for id_ in ids}), ids]
            )

    deduplicate_uuids("pos_order")
    deduplicate_uuids("pos_order_line")
    deduplicate_uuids("pos_payment")
