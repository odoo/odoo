# Part of Odoo. See LICENSE file for full copyright and licensing details.


def migrate(cr, version):
    cr.execute("""
        UPDATE ir_rule r
           SET domain_force = '[
                ("project_id.privacy_visibility", "=", "portal"),
                ("active", "=", True),
                "|",
                    ("message_partner_ids", "child_of", [user.partner_id.commercial_partner_id.id]),
                    ("project_id.collaborator_ids.partner_id", "=", user.partner_id.id),
            ]'
          FROM ir_model_data d
         WHERE d.res_id = r.id
           AND r.domain_force = '[
            (''project_id.privacy_visibility'', ''='', ''portal''),
            (''active'', ''='', True),
            ''|'',
                (''message_partner_ids'', ''child_of'', [user.partner_id.commercial_partner_id.id]),
                (''project_id.collaborator_ids'', ''any'', [
                    (''partner_id'', ''='', user.partner_id.id),
                    (''limited_access'', ''='', False),
                ]),
        ]'
           AND d.model = 'ir.rule'
           AND d.module = 'project'
           AND d.name = 'project_task_rule_portal_project_sharing'
    """)
