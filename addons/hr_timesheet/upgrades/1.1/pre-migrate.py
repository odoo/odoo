# Part of Odoo. See LICENSE file for full copyright and licensing details.


def migrate(cr, version):
    cr.execute("""
        UPDATE ir_rule r
           SET domain_force = '[
                ("project_id", "!=", False),
                "|", "|",
                    ("project_id.privacy_visibility", "!=", "followers"),
                    ("project_id.message_partner_ids", "in", [user.partner_id.id]),
                    ("task_id.message_partner_ids", "in", [user.partner_id.id])
            ]'
          FROM ir_model_data d
         WHERE d.res_id = r.id
           AND d.model = 'ir.rule'
           AND d.module = 'hr_timesheet'
           AND d.name = 'timesheet_line_rule_approver'
    """)

    cr.execute("""
        UPDATE ir_rule r
           SET domain_force = '[
                "|", "|",
                    ("project_id.privacy_visibility", "!=", "followers"),
                    ("project_id.message_partner_ids", "in", [user.partner_id.id]),
                    ("task_id.message_partner_ids", "in", [user.partner_id.id])
            ]'
          FROM ir_model_data d
         WHERE d.res_id = r.id
           AND d.model = 'ir.rule'
           AND d.module = 'hr_timesheet'
           AND d.name = 'timesheet_analysis_report_approver'
    """)
