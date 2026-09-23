import logging

_logger = logging.getLogger(__name__)

MOVED_XMLIDS = (
    (
        "res.groups.privilege",
        "privilege_product_cost",
        "res_groups_privilege_product_cost",
    ),
    ("res.groups", "group_product_cost_readonly", "group_product_cost_readonly"),
    ("res.groups", "group_product_cost_manager", "group_product_cost_manager"),
    (
        "ir.access",
        "access_product_template_cost_manager",
        "access_product_template_cost_manager",
    ),
    (
        "ir.access",
        "access_product_product_cost_manager",
        "access_product_product_cost_manager",
    ),
)


def migrate(cr, version):
    for model, old_name, new_name in MOVED_XMLIDS:
        cr.execute(
            """
            DELETE FROM ir_model_data
            WHERE module = 'marin'
              AND model = %s
              AND name = %s
              AND EXISTS (
                  SELECT 1 FROM ir_model_data
                  WHERE module = 'product'
                    AND model = %s
                    AND name = %s
              )
            """,
            (model, old_name, model, new_name),
        )
        cr.execute(
            """
            UPDATE ir_model_data
            SET module = 'product', name = %s
            WHERE module = 'marin'
              AND model = %s
              AND name = %s
            RETURNING res_id
            """,
            (new_name, model, old_name),
        )
        for [res_id] in cr.fetchall():
            _logger.info(
                "Reassigned marin.%s to product.%s (%s %s)",
                old_name,
                new_name,
                model,
                res_id,
            )
