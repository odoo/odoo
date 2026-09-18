import logging

from lxml import etree

from odoo import api
from odoo.tools import file_path

from .table_inheritance import create_vehicle_table, move_vehicles_into_their_table

_logger = logging.getLogger(__name__)

_BRAND_DATA = "fleet/data/fleet_cars_data.xml"


def _declared_brands() -> list[tuple[str, str]]:
    root = etree.parse(file_path(_BRAND_DATA)).getroot()
    return [
        (record.get("id"), record.findtext('field[@name="name"]'))
        for record in root.iter("record")
        if record.get("model") == "res.partner"
    ]


def adopt_existing_manufacturers(cr) -> int:
    adopted = 0
    for xmlid, name in _declared_brands():
        cr.execute(
            """
            INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
            SELECT 'fleet', %s, 'res.partner', partner.id, FALSE
              FROM res_partner partner
             WHERE partner.is_manufacturer
               AND lower(partner.name) = lower(%s)
               AND NOT EXISTS (
                   SELECT 1 FROM ir_model_data taken
                    WHERE taken.module = 'fleet'
                      AND taken.model = 'res.partner'
                      AND taken.res_id = partner.id
               )
             ORDER BY partner.id
             LIMIT 1
            ON CONFLICT DO NOTHING
            """,
            [xmlid, name],
        )
        adopted += cr.rowcount

    if adopted:
        _logger.info(
            "fleet: %s manufacturer partner(s) already in this database keep their "
            "record and take the matching brand's xml id",
            adopted,
        )
    return adopted


def pre_init_hook(env: api.Environment) -> None:
    create_vehicle_table(env.cr)
    move_vehicles_into_their_table(env.cr)
    adopt_existing_manufacturers(env.cr)
