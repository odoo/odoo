import logging

_logger = logging.getLogger(__name__)

RULES = ["tax_group_comp_rule", "tax_comp_rule", "tax_rep_comp_rule"]


def migrate(cr, version):
    if not version:
        return
    # the three multi-company rules move here from account with the models they guard;
    # re-homing the external ids keeps the records instead of deleting and recreating them
    cr.execute(
        """
        UPDATE ir_model_data
           SET module = 'account_tax'
         WHERE module = 'account'
           AND model = 'ir.access'
           AND (name = ANY(%s) OR name LIKE ANY(%s))
        """,
        [RULES, [name.replace("_", r"\_") + r"\_%" for name in RULES]],
    )
    _logger.info("%s converted access row(s) re-homed to account_tax", cr.rowcount)
