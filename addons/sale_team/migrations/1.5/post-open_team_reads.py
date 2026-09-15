import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_rule r
           SET perm_read = FALSE
          FROM ir_model_data d
         WHERE d.module = 'sale_team'
           AND d.name = 'crm_rule_personal_salesteam'
           AND d.model = 'ir.rule'
           AND d.res_id = r.id
           AND r.perm_read IS TRUE
        """
    )
    if cr.rowcount:
        _logger.info(
            "sale_team: crm_rule_personal_salesteam no longer narrows reads; "
            "a team's row is readable by every internal user, its roster is not"
        )
