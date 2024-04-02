# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

def migrate(cr, version):
    cr.execute("""
      UPDATE ir_rule r
        SET domain_force = '["|", ("employee_id", "=", False), ("employee_id.company_id", "in", company_ids), "|", ("holiday_status_id.company_id", "=", False), ("holiday_status_id.company_id", "in", company_ids)]'
        FROM ir_model_data d
        WHERE d.res_id = r.id
          AND d.model = 'ir.rule'
          AND d.module = 'hr_holidays'
          AND (
            d.name = 'hr_leave_rule_multicompany'
            OR d.name = 'hr_leave_allocation_rule_multicompany'
          )
    """)
