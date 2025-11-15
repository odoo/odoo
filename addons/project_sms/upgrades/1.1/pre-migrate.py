# Part of Odoo. See LICENSE file for full copyright and licensing details.

def migrate(cr, version):
    cr.execute("""
        UPDATE ir_rule r
           SET domain_force = '[(''model'', ''in'', (''project.task'', ''project.project''))]'
          FROM ir_model_data d
         WHERE d.res_id = r.id
           AND r.domain_force = '[(''model_id.model'', ''in'', (''project.task.type'', ''project.project.stage''))]'
           AND d.model = 'ir.rule'
           AND d.module = 'project_sms'
           AND d.name = 'ir_rule_sms_template_project_manager'
    """)
