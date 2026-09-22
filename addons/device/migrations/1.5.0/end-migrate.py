import logging

from odoo import SUPERUSER_ID, api
from odoo.db.schema import table_exists

_logger = logging.getLogger(__name__)

_RELATED_PATH = "device_id.company_id"


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    for model_name, model in env.registry.items():
        field = model._fields.get("company_id")
        if (
            field is None
            or not field.store
            or getattr(field, "related", None) != _RELATED_PATH
        ):
            continue
        table = model._table
        if not table_exists(cr, table):
            continue
        cr.execute(
            f"""
            UPDATE {table} AS log
               SET company_id = device.company_id
              FROM device_device AS device
             WHERE log.device_id = device.id
               AND log.company_id IS NULL
               AND device.company_id IS NOT NULL
            """
        )
        if cr.rowcount:
            _logger.info(
                "19.0.1.5.0: stamped company_id on %s row(s) of %s (%s).",
                cr.rowcount,
                table,
                model_name,
            )
