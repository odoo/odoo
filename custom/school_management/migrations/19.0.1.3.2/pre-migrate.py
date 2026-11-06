"""Repair stale holiday rules before record_rules.xml is imported."""


def migrate(cr, _version):
    cr.execute(
        """
        WITH holiday_model AS (
            SELECT id
              FROM ir_model
             WHERE model = 'university.holiday'
        ), known_holiday_rules AS (
            SELECT data.res_id
              FROM ir_model_data AS data
             WHERE data.module = 'school_management'
               AND data.model = 'ir.rule'
               AND data.name IN ('rule_holiday_registrar', 'rule_holiday_admin')
        )
        UPDATE ir_rule AS rule
           SET model_id = (SELECT id FROM holiday_model),
               domain_force = '[(1, '=', 1)]'
         WHERE rule.id IN (SELECT res_id FROM known_holiday_rules)
            OR (
                rule.domain_force = 'university.holiday'
                AND rule.name ILIKE '%holiday%'
            )
        """
    )
