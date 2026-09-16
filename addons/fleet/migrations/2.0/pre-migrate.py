import logging

_logger = logging.getLogger(__name__)

RETIRED_MODELS = (
    "fleet.vehicle",
    "fleet.vehicle.model",
    "fleet.vehicle.model.brand",
    "fleet.vehicle.model.category",
    "fleet.vehicle.odometer",
    "fleet.vehicle.assignation.log",
    "fleet.vehicle.log.contract",
    "fleet.vehicle.log.services",
    "fleet.vehicle.state",
    "fleet.service.type",
    "fleet.vehicle.cost.report",
    "fleet.vehicle.odometer.report",
)


def migrate(cr, version):
    if not version:
        return
    _drop_views(cr)
    _free_brand_xmlids(cr)


def _drop_views(cr):
    # The vehicle views move from fleet.vehicle to resource.asset under the same xml
    # ids, and every view on a retired model reads fields that no longer exist:
    # left in place, an updated parent would be validated against its old children.
    cr.execute(
        """
        WITH RECURSIVE tree AS (
            SELECT view.id, TRUE AS reloaded
              FROM ir_ui_view view
             WHERE view.model = ANY(%s)
                OR view.id IN (
                    SELECT res_id FROM ir_model_data
                     WHERE module = 'fleet' AND model = 'ir.ui.view'
                )
             UNION
            SELECT view.id,
                   EXISTS (
                       SELECT 1
                         FROM ir_model_data data
                         JOIN ir_module_module module ON module.name = data.module
                        WHERE data.model = 'ir.ui.view'
                          AND data.res_id = view.id
                          AND module.state IN ('installed', 'to upgrade')
                          AND module.name != 'studio_customization'
                   )
              FROM ir_ui_view view
              JOIN tree ON view.inherit_id = tree.id AND tree.reloaded
        )
        SELECT id, reloaded FROM tree
        """,
        [list(RETIRED_MODELS)],
    )
    rows = cr.fetchall()
    kept = [view_id for view_id, reloaded in rows if not reloaded]
    doomed = [view_id for view_id, reloaded in rows if reloaded]
    if kept:
        cr.execute(
            """
            UPDATE ir_ui_view
               SET inherit_id = NULL, mode = 'primary', active = FALSE
             WHERE id = ANY(%s)
         RETURNING id, name
            """,
            [kept],
        )
        for view_id, name in cr.fetchall():
            _logger.warning(
                "View %s (%s) inherited a fleet view that is rebuilt on assets; it is"
                " kept detached and inactive, to be re-applied by hand.",
                view_id,
                name,
            )
    if doomed:
        cr.execute(
            """
            WITH unlinked AS (
                DELETE FROM ir_model_data
                 WHERE model = 'ir.ui.view' AND res_id = ANY(%s)
            )
            DELETE FROM ir_ui_view WHERE id = ANY(%s)
            """,
            [doomed, doomed],
        )


def _free_brand_xmlids(cr):
    # Data and demo files reload before post-migrate, and the same xml ids now name
    # records of other models (a brand is a partner, a model a product, a vehicle an
    # asset). The old rows step aside under a legacy name until post-migrate maps
    # them; a manufacturer partner of the same name takes its brand's xml id, so the
    # data file updates it instead of creating a second one.
    cr.execute(
        """
        UPDATE ir_model_data
           SET name = 'legacy_' || name
         WHERE module = 'fleet' AND model = ANY(%s)
        """,
        [list(RETIRED_MODELS)],
    )
    cr.execute(
        """
        SELECT name, res_id FROM ir_model_data
         WHERE module = 'fleet' AND model = 'fleet.vehicle.model.brand'
        """
    )
    for legacy_name, brand_id in cr.fetchall():
        cr.execute(
            """
            SELECT partner.id
              FROM res_partner partner, fleet_vehicle_model_brand brand
             WHERE brand.id = %s
               AND partner.is_manufacturer
               AND lower(partner.name) = lower(brand.name)
             ORDER BY partner.id
             LIMIT 1
            """,
            [brand_id],
        )
        row = cr.fetchone()
        if row:
            cr.execute(
                """
                INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
                VALUES ('fleet', %s, 'res.partner', %s, FALSE)
                ON CONFLICT DO NOTHING
                """,
                [legacy_name.removeprefix("legacy_"), row[0]],
            )
