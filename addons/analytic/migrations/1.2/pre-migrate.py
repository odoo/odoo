from odoo.tools import sql


def migrate(cr, version):
    # Select relevant ids to generate the list of x_plan_id column names, removing the id of the project plan
    cr.execute(
        """
        SELECT value::int
          FROM ir_config_parameter
         WHERE key = 'analytic.project_plan'
        """
    )
    [project_plan_id] = cr.fetchone()
    cr.execute("SELECT id FROM account_analytic_plan WHERE id != %s AND parent_id IS NULL", [project_plan_id])
    plan_ids = [r[0] for r in cr.fetchall()]
    column_names = [f"x_plan{id_}_id" for id_ in plan_ids]
    # Update on_delete for existing x_plan_id columns
    cr.execute(
        """
        UPDATE ir_model_fields
           SET on_delete = 'restrict'
         WHERE model = 'account.analytic.line'
           AND on_delete = 'set null'
           AND name = ANY(%s)
        """,
        [column_names],
    )
    # Change the constraint on the table definition
    for column in column_names:
        sql.drop_constraint(cr, 'account_analytic_line', f'account_analytic_line_{column}_fkey')
        sql.add_foreign_key(cr, 'account_analytic_line', column, 'account_analytic_account', 'id', 'restrict')
