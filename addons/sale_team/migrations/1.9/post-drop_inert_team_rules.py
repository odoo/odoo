import logging

from odoo.addons.base.models.ir_access_convert import delete_converted_rows

_logger = logging.getLogger(__name__)

# rows that no longer decided any access; 1.5's narrowing of the first one is
# folded into this deletion
RULES = ("crm_rule_personal_salesteam", "crm_rule_all_salesteam")


def migrate(cr, version):
    if not version:
        return
    for name in RULES:
        delete_converted_rows(cr, "sale_team", name, logger=_logger)
