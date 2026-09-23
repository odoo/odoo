import logging

_logger = logging.getLogger(__name__)

REMOVED_FIELDS = (
    ("res.partner", "phone"),
    ("res.partner", "mobile"),
    ("res.users", "work_phone"),
    ("res.users", "mobile_phone"),
    ("res.users", "private_phone"),
    ("res.users", "emergency_phone"),
    ("res.bank", "phone"),
    ("res.partner.bank", "bank_phone"),
    ("crm.lead", "phone"),
    ("event.registration", "phone"),
    ("project.task", "partner_phone"),
    ("pos.order", "mobile"),
    ("hr.applicant", "partner_phone"),
    ("hr.applicant", "partner_phone_sanitized"),
    ("product.msds", "emergency_phone"),
    ("res.partner", "msds_emergency_phone"),
    ("hr.employee", "work_phone"),
    ("hr.employee", "mobile_phone"),
    ("hr.employee", "private_phone"),
    ("hr.employee", "emergency_phone"),
    ("account.asset", "asset_type_kind"),
)

RETIRED_MODELS = ("hr.employee.public",)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT v.id, max(data.module || '.' || data.name)
          FROM ir_ui_view v
          LEFT JOIN ir_model_data data
                 ON data.model = 'ir.ui.view' AND data.res_id = v.id
         WHERE v.model = ANY(%s)
         GROUP BY v.id
         ORDER BY count(v.inherit_id) DESC
        """,
        (list(RETIRED_MODELS),),
    )
    for view_id, xmlid in cr.fetchall():
        if not xmlid:
            _logger.warning(
                "stale views: view %s is declared on a retired model and carries "
                "no xmlid, so nothing would put it back; left in place",
                view_id,
            )
            continue
        cr.execute("DELETE FROM ir_ui_view WHERE inherit_id = %s", (view_id,))
        cr.execute(
            "DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND res_id = %s",
            (view_id,),
        )
        cr.execute("DELETE FROM ir_ui_view WHERE id = %s", (view_id,))
    _logger.info(
        "stale views: dropped the views declared on %s", ", ".join(RETIRED_MODELS)
    )

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
        rows = cr.fetchall()
        doomed = []
        for view_id, _depth, xmlid in rows:
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
