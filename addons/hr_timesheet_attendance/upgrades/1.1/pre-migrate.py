# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


def migrate(cr, version):
    cr.execute("""
        UPDATE ir_rule r
           SET domain_force = '[(1, "=", 1)]'
          FROM ir_model_data d
         WHERE d.res_id = r.id
           AND d.model = 'ir.rule'
           AND d.module = 'hr_timesheet_attendance'
           AND d.name = 'hr_timesheet_attendance_report_rule_approver'
    """)
