import logging

from odoo.addons.base.models.ir_access_convert import delete_converted_rows

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    delete_converted_rows(cr, "sale_team", "crm_rule_team_salesteam", logger=_logger)
