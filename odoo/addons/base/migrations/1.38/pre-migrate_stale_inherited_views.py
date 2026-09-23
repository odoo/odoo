import logging

_logger = logging.getLogger(__name__)

REMOVED_FIELDS = (
    # a bank account belongs to one holder again
    ("res.partner.bank", "partner_ids"),
    ("account.return.type", "payment_partner_ids"),
)


def migrate(cr, version):
    if not version:
        return
    for model, field in REMOVED_FIELDS:
        cr.execute(
            """
            WITH RECURSIVE stale AS (
                SELECT v.id, 0 AS depth
                  FROM ir_ui_view v
                 WHERE v.inherit_id IS NOT NULL AND v.model = %s
                   AND EXISTS (
                       SELECT 1 FROM jsonb_each_text(v.arch_db) arch
                        WHERE arch.value ~ %s
                   )
                 UNION ALL
                SELECT child.id, stale.depth + 1
                  FROM ir_ui_view child
                  JOIN stale ON child.inherit_id = stale.id
            )
            SELECT stale.id, max(stale.depth), max(data.module || '.' || data.name)
              FROM stale
              LEFT JOIN ir_model_data data
                     ON data.model = 'ir.ui.view' AND data.res_id = stale.id
             GROUP BY stale.id
             ORDER BY max(stale.depth) DESC
            """,
            (model, f"name=['\"]{field}['\"]"),
        )
        doomed = []
        for view_id, _depth, xmlid in cr.fetchall():
            if xmlid:
                doomed.append(view_id)
            else:
                _logger.warning(
                    "stale views: view %s on %s names the removed field %s and "
                    "carries no xmlid, so nothing would put it back; left in place",
                    view_id,
                    model,
                    field,
                )
        if not doomed:
            continue
        # Deepest first: ir_ui_view.inherit_id is ON DELETE RESTRICT.
        for view_id in doomed:
            cr.execute(
                "DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND res_id = %s",
                (view_id,),
            )
            cr.execute("DELETE FROM ir_ui_view WHERE id = %s", (view_id,))
        _logger.info(
            "stale views: dropped %s inheriting views that still named %s.%s; "
            "their modules recreate them from corrected source",
            len(doomed),
            model,
            field,
        )
