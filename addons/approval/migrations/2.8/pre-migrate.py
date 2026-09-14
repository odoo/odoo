def migrate(cr, version):
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
