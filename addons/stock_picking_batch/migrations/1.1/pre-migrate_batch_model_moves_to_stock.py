import logging

_logger = logging.getLogger(__name__)

MOVED_RECORDS = [
    ("model_stock_picking_batch", "ir.model"),
    ("access_stock_picking_batch", "ir.access"),
    ("stock_picking_batch_multicompany_rule", "ir.access"),
    ("mt_batch_state", "mail.message.subtype"),
    ("seq_picking_batch", "ir.sequence"),
    ("seq_picking_wave", "ir.sequence"),
]

MOVED_FIELD_OWNERS = ("stock.picking.batch", "stock.picking")


def _repoint(cr, name, model):
    cr.execute(
        """
            UPDATE ir_model_data
               SET module = 'stock'
             WHERE module = 'stock_picking_batch'
               AND name = %s
               AND model = %s
               AND NOT EXISTS (
                   SELECT 1 FROM ir_model_data
                    WHERE module = 'stock' AND name = %s AND model = %s
               )
        """,
        (name, model, name, model),
    )
    return cr.rowcount


def migrate(cr, version):
    moved = sum(_repoint(cr, name, model) for name, model in MOVED_RECORDS)

    cr.execute(
        """
            UPDATE ir_model_data d
               SET module = 'stock'
              FROM ir_model_fields f, ir_model m
             WHERE d.module = 'stock_picking_batch'
               AND d.model = 'ir.model.fields'
               AND d.res_id = f.id
               AND f.model_id = m.id
               AND m.model = ANY(%s)
               AND NOT EXISTS (
                   SELECT 1 FROM ir_model_data e
                    WHERE e.module = 'stock'
                      AND e.name = d.name
                      AND e.model = 'ir.model.fields'
               )
        """,
        (list(MOVED_FIELD_OWNERS),),
    )
    _logger.info(
        "repointed %s records and %s field declarations at stock", moved, cr.rowcount
    )
