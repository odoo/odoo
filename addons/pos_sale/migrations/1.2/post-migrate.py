from odoo.tools import SQL


def migrate(cr, version):
    if not version:
        return
    # the rule gave POS managers every crm.team, which held sales teams only;
    # on team.team the same domain would reach every application's teams
    cr.execute(
        SQL(
            """
            UPDATE ir_rule r SET domain_force = %s
              FROM ir_model_data d
             WHERE d.module = 'pos_sale' AND d.name = 'pos_sale_rule_pos_channel_pos_manager'
               AND d.model = 'ir.rule' AND d.res_id = r.id
            """,
            "[('use_sale', '=', True)]",
        )
    )
