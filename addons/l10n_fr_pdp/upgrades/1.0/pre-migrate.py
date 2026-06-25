from odoo.tools import SQL


def migrate(cr, version):
    obsolete_view_xmlids = (
        'l10n_fr_pdp_reports_view_move_search',
        'l10n_fr_pdp_reports_view_move_kanban',
        'l10n_fr_pdp_reports_view_in_invoice_tree',
        'l10n_fr_pdp_reports_view_move_form',
        'l10n_fr_pdp_reports_view_out_credit_note_tree',
        'l10n_fr_pdp_reports_view_out_invoice_tree',
    )
    obsolete_field_names = ('l10n_fr_pdp_error_message', 'l10n_fr_pdp_display_info')
    obsolete_field_models = ('account.move', 'account.bank.statement.line')

    cr.execute(SQL(
        """
        WITH obsolete_views AS (
            SELECT res_id
              FROM ir_model_data
             WHERE module = 'l10n_fr_pdp'
               AND model = 'ir.ui.view'
               AND name IN %s
        )
        DELETE FROM ir_ui_view
              WHERE id IN (SELECT res_id FROM obsolete_views)
        """,
        obsolete_view_xmlids,
    ))
    cr.execute(SQL(
        """
        DELETE FROM ir_model_data
              WHERE module = 'l10n_fr_pdp'
                AND model = 'ir.ui.view'
                AND name IN %s
        """,
        obsolete_view_xmlids,
    ))

    cr.execute(SQL(
        """
        WITH obsolete_fields AS (
            SELECT id
              FROM ir_model_fields
             WHERE model IN %s
               AND name IN %s
        )
        DELETE FROM ir_model_data
              WHERE model = 'ir.model.fields'
                AND module = 'l10n_fr_pdp'
                AND res_id IN (SELECT id FROM obsolete_fields)
        """,
        obsolete_field_models,
        obsolete_field_names,
    ))
    cr.execute(SQL(
        """
        DELETE FROM ir_model_fields
              WHERE model IN %s
                AND name IN %s
        """,
        obsolete_field_models,
        obsolete_field_names,
    ))
