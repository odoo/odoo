def migrate(cr, version):
    cr.execute(
        """
        DELETE FROM ir_rule
              WHERE id IN (SELECT res_id
                             FROM ir_model_data
                            WHERE module = 'sale_team'
                              AND name = 'crm_rule_team_salesteam'
                              AND model = 'ir.rule')
        """
    )
    cr.execute(
        """
        DELETE FROM ir_model_data
              WHERE module = 'sale_team'
                AND name = 'crm_rule_team_salesteam'
        """
    )
