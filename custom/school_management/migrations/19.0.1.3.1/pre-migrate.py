"""Repair holiday rules created by the pre-release security XML."""


def migrate(cr, _version):
    cr.execute(
        """
        UPDATE ir_rule AS rule
           SET model_id = model.id,
               domain_force = '[(1, '=', 1)]'
          FROM ir_model_data AS data,
               ir_model AS model
         WHERE data.module = 'school_management'
           AND data.name IN ('rule_holiday_registrar', 'rule_holiday_admin')
           AND data.model = 'ir.rule'
           AND data.res_id = rule.id
           AND model.model = 'university.holiday'
        """
    )
