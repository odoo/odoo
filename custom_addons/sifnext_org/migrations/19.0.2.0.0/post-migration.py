import logging

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    departments = env["hr.department"].sudo().with_context(active_test=False).search([
        ("sif_code", "=", False),
    ])
    for department in departments:
        code = env["ir.sequence"].next_by_code("sifnext.department.code")
        if not code:
            raise RuntimeError("The SIF department code sequence is missing.")
        department.write({"sif_code": code})

    _logger.info("Assigned SIF department codes to %s existing departments.", len(departments))
