import logging

_logger = logging.getLogger(__name__)

RULES = ("crm_rule_personal_salesteam", "crm_rule_all_salesteam")


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        DELETE FROM ir_rule
              WHERE id IN (SELECT res_id
                             FROM ir_model_data
                            WHERE module = 'sale_team'
                              AND name = ANY(%s)
                              AND model = 'ir.rule')
        """,
        (list(RULES),),
    )
    deleted = cr.rowcount
    cr.execute(
        """
        DELETE FROM ir_model_data
              WHERE module = 'sale_team'
                AND name = ANY(%s)
                AND model = 'ir.rule'
        """,
        (list(RULES),),
    )
    if deleted:
        _logger.info(
            "sale_team: deleted %s crm.team record rule(s) that no longer "
            "decided any access",
            deleted,
        )
