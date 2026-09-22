import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    for xmlid in (
        "device.device_device_company_rule",
        "device.device_data_log_company_rule",
    ):
        rule = env.ref(xmlid, raise_if_not_found=False)
        if rule and "company_id', '=', False" in (rule.domain_force or ""):
            rule.domain_force = "[('company_id', 'in', company_ids)]"
            _logger.info(
                "19.0.1.5.0: scoped %s strictly to the user's companies.", xmlid
            )

    cr.execute("SELECT id FROM res_company ORDER BY id LIMIT 1")
    row = cr.fetchone()
    if not row:
        return
    company_id = row[0]

    cr.execute(
        "UPDATE device_device SET company_id = %s WHERE company_id IS NULL",
        (company_id,),
    )
    devices_fixed = cr.rowcount
    if devices_fixed:
        _logger.info(
            "19.0.1.5.0: assigned company %s to %s device(s) that had none.",
            company_id,
            devices_fixed,
        )
