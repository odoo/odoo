def migrate(cr, version):
    _release_routing_columns(cr)
    cr.execute(
        """
        WITH steps_view AS (
            DELETE FROM ir_model_data
             WHERE module = 'approval'
               AND name = 'approval_category_view_form_steps'
               AND model = 'ir.ui.view'
         RETURNING res_id
        )
        DELETE FROM ir_ui_view WHERE id IN (SELECT res_id FROM steps_view)
        """
    )


def _release_routing_columns(cr):
    # 19.0.2.8.0 routes by steps and takes group_approval off the model, but
    # the column stays behind with its NOT NULL: the end-migration still reads
    # it to build each category's step. Without a default, every category a
    # data file creates during this upgrade then fails to insert.
    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_name = 'approval_category'
           AND column_name = 'group_approval'
           AND is_nullable = 'NO'
        """
    )
    if cr.fetchone():
        cr.execute(
            "ALTER TABLE approval_category ALTER COLUMN group_approval DROP NOT NULL"
        )
